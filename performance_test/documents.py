"""Generate valid test documents of an exact size.

The publicatiebank strips metadata from uploaded PDF and ZIP files in a celery task
(download from the Documents API, strip, re-upload). That pipeline only runs - and can
only succeed - when the uploaded file is a real document, so random bytes labelled as a
PDF won't do. The generators below produce well-formed files whose bulk is random
(incompressible) data:

* ``pdf`` - a one page PDF with a greyscale image of random pixels, plus an info
  dictionary so there is metadata to strip.
* ``zip`` - a ZIP archive with one stored (uncompressed) member and a comment.
* ``bin`` - plain random bytes (``application/octet-stream``); not stripped, so the
  upload completes as soon as the last part is received.
"""

from __future__ import annotations

import io
import math
import os
import random
import re
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, assert_never

MiB = 1024 * 1024


@dataclass(frozen=True)
class FileType:
    extension: str
    content_type: str


type FileTypeName = Literal["pdf", "zip", "bin"]

FILE_TYPES: Mapping[FileTypeName, FileType] = {
    "pdf": FileType("pdf", "application/pdf"),
    "zip": FileType("zip", "application/zip"),
    "bin": FileType("bin", "application/octet-stream"),
}


@dataclass(frozen=True)
class SizeRange:
    """Document size in bytes: fixed, or log-uniformly distributed over a range.

    Log-uniform means there are as many documents between 1-10 MiB as between
    10-100 MiB, which resembles real document collections better than a flat
    distribution: mostly small files with an occasional big one.
    """

    low: int
    high: int

    @classmethod
    def parse(cls, value: str) -> SizeRange:
        """Parse ``"5"`` or ``"0.5-50"`` (MiB)."""
        if not (match := re.fullmatch(r"\s*([\d.]+)\s*(?:-\s*([\d.]+)\s*)?", value)):
            raise ValueError(
                f"Invalid document size {value!r}, expected e.g. 5 or 1-50"
            )
        low = float(match[1])
        high = float(match[2] or match[1])
        if not 0 < low <= high:
            raise ValueError(f"Invalid document size range {value!r}")
        return cls(int(low * MiB), int(high * MiB))

    def sample(self) -> int:
        if self.low == self.high:
            return self.low
        return int(math.exp(random.uniform(math.log(self.low), math.log(self.high))))


_random_pool = b""


def _random_bytes(size: int) -> bytes:
    """Return ``size`` random bytes, reusing one shared pool.

    Generating hundreds of MiB of random data per document would make the load
    generator the bottleneck; the content (probably) does not need to differ between
    documents.
    """
    global _random_pool
    if len(_random_pool) < size:
        _random_pool = os.urandom(size)
    return _random_pool[:size]


def make_document(file_type: FileTypeName, size: int) -> bytes:
    """Return a valid document of ``file_type`` that is exactly ``size`` bytes."""
    match file_type:
        case "pdf":
            return _make_pdf(size)
        case "zip":
            return _make_zip(size)
        case "bin":
            return _random_bytes(size)
        case _:
            assert_never(file_type)


_PDF_IMAGE_WIDTH = 1024


def _pdf_bytes(pixels: bytes, padding: int) -> bytes:
    height = max(1, math.ceil(len(pixels) / _PDF_IMAGE_WIDTH))
    pixels = pixels.ljust(_PDF_IMAGE_WIDTH * height, b"\0")
    content = b"q 595 0 0 842 0 0 cm /Im0 Do Q"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        b"<< /Type /XObject /Subtype /Image /Width %d /Height %d "
        b"/ColorSpace /DeviceGray /BitsPerComponent 8 /Length %d >>\nstream\n"
        % (_PDF_IMAGE_WIDTH, height, len(pixels))
        + pixels
        + b"\nendstream",
        b"<< /Title (Prestatietest) /Author (GPP performance test) "
        b"/Producer (performance_test/documents.py) /Keywords (%s) >>"
        % (b"x" * padding),
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n%s\nendobj\n" % (number, body))
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for offset in offsets:
        out.write(b"%010d 00000 n \n" % offset)
    out.write(
        b"trailer\n<< /Size %d /Root 1 0 R /Info 6 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objects) + 1, xref)
    )
    return out.getvalue()


def _make_pdf(size: int) -> bytes:
    # The image height is rounded up to whole rows, so size the pixel data to a
    # multiple of the row width and make up the remainder with padding in the
    # metadata. The xref offsets grow by a few digits at most as the padding changes,
    # so a couple of iterations converge on the exact size.
    overhead = len(_pdf_bytes(b"", 0)) - _PDF_IMAGE_WIDTH
    pixel_count = max(
        _PDF_IMAGE_WIDTH,
        (size - overhead) // _PDF_IMAGE_WIDTH * _PDF_IMAGE_WIDTH,
    )
    pixels = _random_bytes(pixel_count)
    padding = 0
    document = _pdf_bytes(pixels, padding)
    for _ in range(5):
        if len(document) == size:
            break
        padding = max(0, padding + size - len(document))
        document = _pdf_bytes(pixels, padding)
    # if the size still differs, it is smaller than the smallest valid PDF
    return document


def _zip_bytes(member_size: int) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, mode="w", compression=zipfile.ZIP_STORED) as archive:
        archive.comment = b"GPP performance test"
        archive.writestr("prestatietest.bin", _random_bytes(member_size))
    return out.getvalue()


def _make_zip(size: int) -> bytes:
    overhead = len(_zip_bytes(0))
    return _zip_bytes(max(0, size - overhead))
