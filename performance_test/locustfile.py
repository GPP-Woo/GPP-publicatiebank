"""Load test for a deployed GPP Publicatiebank.

Three kinds of users, each with its own count:

``Reader``
    An API consumer (GPP-app, GPP-zoeken, burgerportaal) browsing: lists and retrieves
    publications, documents and the reference data, and downloads documents.
``Editor``
    Works on publication metadata: creates a concept publication, edits it and
    deletes it again.
``Uploader``
    The bulk upload from issue #465: creates a concept publication with one or more
    documents, uploads all file parts, waits until the publicatiebank reports the
    upload as complete (which includes the metadata stripping in celery), downloads
    the result and checks its size, then deletes everything it created.

Besides the per-request statistics, the uploader reports the full pipeline as
``FLOW document ready``: the time from registering a document until it is complete
and downloadable. It fails when a step fails, when the document is not complete within
``--completion-timeout``, or when the stored file is wrong (truncated, or much larger
than the upload).

Usage (see the documentation for more)::

    locust -f performance_test/locustfile.py --host https://publicatiebank.example.nl \\
        --token <api key> --readers 20 --editors 5 --uploaders 3 --doc-size-mb 1-50

Everything a run creates is a *concept* publication with "Prestatietest" in the
title, so it is never published, and it is removed at the end of each iteration
unless ``--keep-data`` is given.
"""

from __future__ import annotations

import logging  # noqa: TID251 - standalone tool, structlog is not installed
import math
import random
import time
import uuid
from argparse import Namespace
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any, Literal, NamedTuple, TypedDict, overload
from urllib.parse import urlsplit

from documents import FILE_TYPES, SizeRange, make_document
from locust import HttpUser, between, events, task
from locust.argument_parser import LocustArgumentParser
from locust.env import Environment
from locust.exception import StopUser
from requests import Response

logger = logging.getLogger(__name__)

API = "/api/v2"
REQUEST_TIMEOUT = 1800  # seconds; matches the default uwsgi http-timeout/harakiri
POLL_INTERVAL = 2  # seconds between checks whether an upload is complete
MAX_GROWTH = 1.1  # largest acceptable stored size / uploaded size

type Method = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]


# The parts of the API responses the test relies on.
class Publication(TypedDict):
    uuid: str


class FilePart(TypedDict):
    url: str
    volgnummer: int
    omvang: int


class Document(TypedDict):
    uuid: str
    uploadVoltooid: bool
    bestandsomvang: int
    bestandsdelen: Sequence[FilePart]


class Page[T](TypedDict):
    count: int
    results: Sequence[T]


class PendingDocument(NamedTuple):
    """A document whose parts are uploaded, waiting to be completely processed."""

    uuid: str
    started: float  # time.monotonic() when the document was registered
    size: int  # bytes uploaded


@events.init_command_line_parser.add_listener
def _(parser: LocustArgumentParser, **kwargs: object) -> None:
    parser.add_argument(
        "--token",
        env_var="PERF_TOKEN",
        default="",
        is_secret=True,
        help="API key of the publicatiebank (Admin > API > API keys).",
    )
    parser.add_argument(
        "--readers",
        type=int,
        env_var="PERF_READERS",
        default=10,
        help="Number of users that browse and download (default 10).",
    )
    parser.add_argument(
        "--editors",
        type=int,
        env_var="PERF_EDITORS",
        default=2,
        help="Number of users that create and edit publications (default 2).",
    )
    parser.add_argument(
        "--uploaders",
        type=int,
        env_var="PERF_UPLOADERS",
        default=2,
        help="Number of users that upload documents (default 2).",
    )
    parser.add_argument(
        "--doc-size-mb",
        env_var="PERF_DOC_SIZE_MB",
        default="1-20",
        help="Size of each uploaded document in MiB: a number, or a range like 1-50 "
        "(sizes are then spread log-uniformly: mostly small, some large). "
        "Default 1-20.",
    )
    parser.add_argument(
        "--docs-per-publication",
        type=int,
        env_var="PERF_DOCS_PER_PUBLICATION",
        default=1,
        help="Documents an uploader adds to each publication (default 1).",
    )
    parser.add_argument(
        "--file-type",
        env_var="PERF_FILE_TYPE",
        choices=sorted(FILE_TYPES),
        default="pdf",
        help="pdf and zip go through metadata stripping in celery, bin does not "
        "(default pdf).",
    )
    parser.add_argument(
        "--completion-timeout",
        type=int,
        env_var="PERF_COMPLETION_TIMEOUT",
        default=600,
        help="Seconds to wait for an upload to complete (default 600).",
    )
    parser.add_argument(
        "--keep-data",
        action="store_true",
        env_var="PERF_KEEP_DATA",
        help="Do not delete the publications and documents the test created.",
    )


def _user_counts(options: Namespace) -> Mapping[type[PublicatiebankUser], int]:
    return {
        Reader: options.readers,
        Editor: options.editors,
        Uploader: options.uploaders,
    }


@events.init.add_listener
def _(environment: Environment, **kwargs: object) -> None:
    options = environment.parsed_options
    if options is None:
        return
    SizeRange.parse(options.doc_size_mb)  # fail early on a typo
    # without -u/--users, start exactly the requested users of each kind
    if not options.num_users:
        options.num_users = sum(_user_counts(options).values())


@events.test_start.add_listener
def _(environment: Environment, **kwargs: object) -> None:
    options = environment.parsed_options
    if options is None:
        return
    counts = _user_counts(options)
    for user_class, count in counts.items():
        user_class.fixed_count = count
    total = sum(counts.values())
    if total == 0:
        logger.error("--readers, --editors and --uploaders are all 0, nothing to do")
    elif (target := getattr(environment.runner, "target_user_count", total)) != total:
        logger.warning(
            "Number of users (%s) differs from readers + editors + uploaders (%s), "
            "the run will not have the requested mix. Leave out -u/--users in "
            "headless mode, or enter the total in the web UI.",
            target,
            total,
        )


class PublicatiebankUser(HttpUser):
    abstract = True

    def on_start(self) -> None:
        self._information_categories: list[str] = []
        self._created: set[str] = set()  # publications not deleted yet
        options = self.environment.parsed_options
        if not options.token:
            raise StopUser("No API key: pass --token or set PERF_TOKEN")
        self.client.headers.update(
            {
                "Authorization": f"Token {options.token}",
                "Accept": "application/json",
                # the API requires the audit headers on every request
                "Audit-User-ID": "prestatietest",
                "Audit-User-Representation": "Prestatietest",
                "Audit-Remarks": "Performance test (performance_test/locustfile.py)",
            }
        )

    def request(
        self,
        method: Method,
        path: str,
        name: str | None = None,
        gone_status: int | None = None,
        **kwargs: Any,
    ) -> Response:
        """Do a request, failing it on any non-2xx status.

        ``path`` may be an absolute URL returned by the API; only its path is used, so
        the request always goes to ``--host`` (the API builds URLs from the Host
        header, which may not resolve from where the test runs).

        A response with ``gone_status`` counts as a success: other users of the test
        delete what they created, possibly right after it showed up in a list. That
        gives a 404 on the object itself, and a 400 when filtering on it.
        """
        parts = urlsplit(path)
        path = parts.path + (f"?{parts.query}" if parts.query else "")
        kwargs.setdefault("timeout", REQUEST_TIMEOUT)
        with self.client.request(
            method, path, name=name or path, catch_response=True, **kwargs
        ) as response:
            if response.status_code == gone_status:
                response.success()
            elif not response.ok:
                response.failure(f"HTTP {response.status_code}: {response.text[:300]}")
            return response

    def get_json(self, path: str, name: str | None = None, **kwargs: Any) -> Any:
        """Return the parsed body, or ``None`` on an error status.

        The JSON is not validated: callers annotate the result with the TypedDict of
        the response they expect.
        """
        response = self.request("GET", path, name, **kwargs)
        return response.json() if response.ok else None

    def pick_information_category(self) -> str | None:
        if not self._information_categories:
            data: Page[Publication] | None = self.get_json(
                f"{API}/informatiecategorieen"
            )
            self._information_categories = [
                item["uuid"] for item in (data["results"] if data else [])
            ]
        if not self._information_categories:
            return None
        return random.choice(self._information_categories)

    def create_publication(self) -> Publication | None:
        category = self.pick_information_category()
        if category is None:
            return None
        response = self.request(
            "POST",
            f"{API}/publicaties",
            json={
                "officieleTitel": f"Prestatietest {uuid.uuid4()}",
                "omschrijving": "Aangemaakt door de prestatietest.",
                "publicatiestatus": "concept",
                "informatieCategorieen": [category],
            },
        )
        if not response.ok:
            return None
        publication: Publication = response.json()
        self._created.add(publication["uuid"])
        return publication

    def on_stop(self) -> None:
        # The run can end in the middle of an iteration, clean up what is left.
        for publication_uuid in list(self._created):
            self.delete_publication(publication_uuid)

    def delete_publication(self, publication_uuid: str) -> None:
        if self.environment.parsed_options.keep_data:
            return
        self._created.discard(publication_uuid)
        # Deleting a publication leaves its files in the Documents API, deleting the
        # documents first removes those too.
        documents: Page[Document] | None = self.get_json(
            f"{API}/documenten?publicatie={publication_uuid}",
            name=f"{API}/documenten?publicatie=[uuid]",
        )
        for document in documents["results"] if documents else []:
            self.request(
                "DELETE",
                f"{API}/documenten/{document['uuid']}",
                name=f"{API}/documenten/[uuid]",
            )
        self.request(
            "DELETE",
            f"{API}/publicaties/{publication_uuid}",
            name=f"{API}/publicaties/[uuid]",
        )


class Reader(PublicatiebankUser):
    wait_time = between(1, 5)

    def on_start(self) -> None:
        super().on_start()
        self._pages: dict[str, int] = {}

    @overload
    def get_page(
        self, resource: Literal["publicaties"]
    ) -> Page[Publication] | None: ...
    @overload
    def get_page(self, resource: Literal["documenten"]) -> Page[Document] | None: ...
    def get_page(
        self, resource: Literal["publicaties", "documenten"]
    ) -> Page[Publication] | Page[Document] | None:
        """Get a random page (of the first five) of a list endpoint."""
        page = random.randint(1, self._pages.get(resource, 1))
        data: Page[Any] | None = self.get_json(
            f"{API}/{resource}?page={page}",
            name=f"{API}/{resource}?page=[n]",
            gone_status=404,  # the list got shorter
        )
        if data is None:
            self._pages.pop(resource, None)
        if data and data["results"]:
            pages = math.ceil(data["count"] / len(data["results"]))
            self._pages[resource] = min(5, pages)
        return data

    @task(4)
    def browse_publications(self) -> None:
        page = self.get_page("publicaties")
        if not page or not page["results"]:
            return
        publication = random.choice(page["results"])
        self.get_json(
            f"{API}/publicaties/{publication['uuid']}",
            name=f"{API}/publicaties/[uuid]",
            gone_status=404,
        )
        documents: Page[Document] | None = self.get_json(
            f"{API}/documenten?publicatie={publication['uuid']}",
            name=f"{API}/documenten?publicatie=[uuid]",
            gone_status=400,
        )
        if documents and documents["results"]:
            document = random.choice(documents["results"])
            self.get_json(
                f"{API}/documenten/{document['uuid']}",
                name=f"{API}/documenten/[uuid]",
                gone_status=404,
            )

    @task(2)
    def browse_documents(self) -> None:
        self.get_page("documenten")

    @task(1)
    def download_document(self) -> None:
        documents = self.get_page("documenten")
        complete = [
            d
            for d in (documents["results"] if documents else [])
            if d["uploadVoltooid"]
        ]
        if complete:
            document = random.choice(complete)
            self.request(
                "GET",
                f"{API}/documenten/{document['uuid']}/download",
                name=f"{API}/documenten/[uuid]/download",
                headers={"Accept": "*/*"},
                gone_status=404,
            )

    @task(2)
    def reference_data(self) -> None:
        resource = random.choice(
            ["informatiecategorieen", "themas", "onderwerpen", "organisaties"]
        )
        self.get_json(f"{API}/{resource}")


class Editor(PublicatiebankUser):
    wait_time = between(2, 10)

    @task
    def edit_publication(self) -> None:
        publication = self.create_publication()
        if publication is None:
            return
        path = f"{API}/publicaties/{publication['uuid']}"
        name = f"{API}/publicaties/[uuid]"
        self.get_json(path, name=name)
        self.request(
            "PATCH",
            path,
            name=name,
            json={"omschrijving": "Bijgewerkt door de prestatietest."},
        )
        self.get_json(
            f"{API}/publicaties?search=Prestatietest",
            name=f"{API}/publicaties?search=[term]",
        )
        self.delete_publication(publication["uuid"])


class Uploader(PublicatiebankUser):
    wait_time = between(1, 3)

    @task
    def upload_publication(self) -> None:
        options = self.environment.parsed_options
        publication = self.create_publication()
        if publication is None:
            return
        try:
            started = [
                self.upload_document(publication["uuid"])
                for _ in range(options.docs_per_publication)
            ]
            for pending in filter(None, started):
                self.wait_until_ready(pending)
        finally:
            self.delete_publication(publication["uuid"])

    def upload_document(self, publication_uuid: str) -> PendingDocument | None:
        """Register a document and upload its parts; return what to wait for."""
        options = self.environment.parsed_options
        file_type = FILE_TYPES[options.file_type]
        size = SizeRange.parse(options.doc_size_mb).sample()
        content = make_document(options.file_type, size)

        started = time.monotonic()
        response = self.request(
            "POST",
            f"{API}/documenten",
            json={
                "publicatie": publication_uuid,
                "officieleTitel": "Prestatietest document",
                "creatiedatum": date.today().isoformat(),
                "bestandsnaam": f"prestatietest.{file_type.extension}",
                "bestandsformaat": file_type.content_type,
                "bestandsomvang": size,
            },
        )
        if not response.ok:
            self.report_ready(started, size, f"create failed ({response.status_code})")
            return None
        document: Document = response.json()

        offset = 0
        for part in sorted(document["bestandsdelen"], key=lambda p: p["volgnummer"]):
            chunk = content[offset : offset + part["omvang"]]
            offset += part["omvang"]
            response = self.request(
                "PUT",
                part["url"],
                name=f"{API}/documenten/[uuid]/bestandsdelen/[uuid]",
                files={"inhoud": (f"part.{file_type.extension}", chunk)},
            )
            if not response.ok:
                self.report_ready(
                    started, size, f"part upload failed ({response.status_code})"
                )
                return None
        return PendingDocument(document["uuid"], started, size)

    def wait_until_ready(self, pending: PendingDocument) -> None:
        """Poll until the upload (including metadata stripping) is complete."""
        document_uuid, started, size = pending
        deadline = started + self.environment.parsed_options.completion_timeout
        path = f"{API}/documenten/{document_uuid}"
        while True:
            data: Document | None = self.get_json(
                path, name=f"{API}/documenten/[uuid] (poll)"
            )
            if data is None:
                self.report_ready(started, size, "document could not be retrieved")
                return
            if data["uploadVoltooid"]:
                break
            if time.monotonic() > deadline:
                self.report_ready(started, size, "upload did not complete in time")
                return
            time.sleep(POLL_INTERVAL)

        # the stored file may differ from the upload after stripping its metadata
        response = self.request(
            "GET",
            f"{path}/download",
            name=f"{API}/documenten/[uuid]/download",
            headers={"Accept": "*/*"},
        )
        if not response.ok:
            self.report_ready(
                started, size, f"download failed ({response.status_code})"
            )
        elif data["bestandsomvang"] > size * MAX_GROWTH:
            # stripping metadata may change the size a little, never this much
            self.report_ready(
                started,
                size,
                f"stored file is {data['bestandsomvang'] / size:.1f}x the upload",
            )
        elif len(response.content) != data["bestandsomvang"]:
            self.report_ready(
                started,
                size,
                f"downloaded {len(response.content)} bytes, "
                f"expected {data['bestandsomvang']}",
            )
        else:
            self.report_ready(started, size)

    def report_ready(self, started: float, size: int, error: str | None = None) -> None:
        self.environment.events.request.fire(
            request_type="FLOW",
            name="document ready",
            response_time=(time.monotonic() - started) * 1000,
            response_length=size,
            exception=Exception(error) if error else None,
            context={},
        )
