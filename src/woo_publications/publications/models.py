import uuid
from functools import partial
from typing import Callable
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import models, transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework.reverse import reverse
from zgw_consumers.constants import APITypes

from woo_publications.accounts.models import User
from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.documents_api.client import (
    Document as ZGWDocument,
    get_client,
)
from woo_publications.logging.serializing import serialize_instance
from woo_publications.logging.service import (
    ModelOwnerMixin,
    audit_admin_update,
    audit_api_update,
)
from woo_publications.logging.typing import ActingUser
from woo_publications.metadata.constants import InformationCategoryOrigins
from woo_publications.metadata.models import InformationCategory
from woo_publications.metadata.service import get_inspannings_verplichting

from .constants import (
    DOCUMENT_ACTION_TOOI_IDENTIFIERS,
    DocumentActionTypeOptions,
    PublicationStatusOptions,
)
from .typing import DocumentActions

# when the document isn't specified both the service and uuid needs to be unset
_DOCUMENT_NOT_SET = models.Q(document_service=None, document_uuid=None)
# when the document is specified both the service and uuid needs to be set
_DOCUMENT_SET = ~models.Q(document_service=None) & ~models.Q(document_uuid=None)


class Publication(ModelOwnerMixin, models.Model):
    id: int  # implicitly provided by django
    uuid = models.UUIDField(
        _("UUID"),
        unique=True,
        default=uuid.uuid4,
        editable=False,
    )
    informatie_categorieen = models.ManyToManyField(
        "metadata.informationcategory",
        verbose_name=_("information categories"),
        help_text=_(
            "The information categories clarify the kind of information present in the publication."
        ),
    )
    publisher = models.ForeignKey(
        "metadata.organisation",
        verbose_name=_("publisher"),
        related_name="published_publications",
        help_text=_("The organisation which publishes the publication."),
        limit_choices_to={"is_actief": True},
        on_delete=models.CASCADE,
    )
    verantwoordelijke = models.ForeignKey(
        "metadata.organisation",
        verbose_name=_("liable organisation"),
        related_name="liable_for_publications",
        help_text=_(
            "The organisation which is liable for the publication and its contents."
        ),
        limit_choices_to={"is_actief": True},
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    opsteller = models.ForeignKey(
        "metadata.organisation",
        verbose_name=_("drafter"),
        related_name="drafted_publications",
        help_text=_("The organisation which drafted the publication and its content."),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    officiele_titel = models.CharField(
        _("official title"),
        max_length=255,
    )
    verkorte_titel = models.CharField(
        _("short title"),
        max_length=255,
        blank=True,
    )
    omschrijving = models.TextField(_("description"), blank=True)
    publicatiestatus = models.CharField(
        _("status"),
        max_length=12,
        choices=PublicationStatusOptions.choices,
        default=PublicationStatusOptions.published,
    )
    registratiedatum = models.DateTimeField(
        _("created on"),
        auto_now_add=True,
        editable=False,
        help_text=_(
            "System timestamp reflecting when the publication was registered in the "
            "database. Not to be confused with the creation date of the publication, "
            "which is usually *before* the registration date."
        ),
    )
    laatst_gewijzigd_datum = models.DateTimeField(
        _("last modified"),
        auto_now=True,
        editable=False,
        help_text=_(
            "System timestamp reflecting when the publication was last modified in the "
            "database."
        ),
    )

    class Meta:  # pyright: ignore
        verbose_name = _("publication")
        verbose_name_plural = _("publications")

    def __str__(self):
        return self.officiele_titel

    def clean(self):
        super().clean()
        if not self.pk and self.publicatiestatus == PublicationStatusOptions.revoked:
            raise ValidationError(
                _("You cannot create a {revoked} publication.").format(
                    revoked=PublicationStatusOptions.revoked.label.lower()
                )
            )

    def revoke_own_published_documents(
        self, user: User | ActingUser, remarks: str | None = None
    ) -> None:
        from .tasks import remove_document_from_index

        published_documents = (
            self.document_set.filter(  # pyright: ignore[reportAttributeAccessIssue]
                publicatiestatus=PublicationStatusOptions.published
            )
        )

        # get a list of IDs of published documents, make sure to evaluate the queryset so it's not affected by
        # the `update` query
        document_ids_to_log = list(published_documents.values_list("pk", flat=True))
        for document_id in document_ids_to_log:
            transaction.on_commit(
                partial(remove_document_from_index.delay, document_id=document_id)
            )

        published_documents.update(
            publicatiestatus=PublicationStatusOptions.revoked,
            laatst_gewijzigd_datum=timezone.now(),
        )

        # audit log actions
        is_django_user = isinstance(user, User)
        log_callback = audit_admin_update if is_django_user else audit_api_update
        log_extra_kwargs = (
            {"django_user": user}
            if is_django_user
            else {
                "user_id": user["identifier"],
                "user_display": user["display_name"],
                "remarks": remarks,
            }
        )
        for document in Document.objects.filter(pk__in=document_ids_to_log):
            log_callback(
                content_object=document,
                object_data=serialize_instance(document),
                **log_extra_kwargs,  # pyright: ignore[reportArgumentType]
            )

    @property
    def get_diwoo_informatie_categorieen_uuids(
        self,
    ) -> models.QuerySet[InformationCategory, UUID]:
        return (
            self.informatie_categorieen.annotate(
                sitemap_uuid=models.Case(
                    models.When(
                        oorsprong=InformationCategoryOrigins.custom_entry,
                        then=models.Value(get_inspannings_verplichting().uuid),
                    ),
                    default=models.F("uuid"),
                )
            )
            .order_by("sitemap_uuid")
            .distinct("sitemap_uuid")
            .values_list("sitemap_uuid", flat=True)
        )


class Document(ModelOwnerMixin, models.Model):
    id: int  # implicitly provided by django
    uuid = models.UUIDField(
        _("UUID"),
        unique=True,
        default=uuid.uuid4,
        editable=False,
    )
    publicatie = models.ForeignKey(
        Publication,
        verbose_name=_("publication"),
        help_text=_(
            "The publication that this document belongs to. A publication may have "
            "zero or more documents."
        ),
        on_delete=models.CASCADE,
    )
    identifier = models.CharField(
        _("identifier"),
        help_text=_("The (primary) unique identifier."),
        max_length=255,
        blank=True,
    )
    officiele_titel = models.CharField(
        _("official title"),
        max_length=255,
    )
    verkorte_titel = models.CharField(
        _("short title"),
        max_length=255,
        blank=True,
    )
    omschrijving = models.TextField(_("description"), blank=True)
    creatiedatum = models.DateField(
        _("creation date"),
        help_text=_(
            "Date when the (physical) document came into existence. Not to be confused "
            "with the registration timestamp of the document - the creation date is "
            "typically *before* the registration date."
        ),
    )
    bestandsformaat = models.CharField(
        _("file format"),
        max_length=255,
        help_text=_(
            "TODO - placeholder accepting anything, in the future this will be "
            "validated against a reference value list."
        ),
        default="unknown",  # TODO: remove this once the formats are set up properly
    )
    bestandsnaam = models.CharField(
        _("file name"),
        max_length=255,
        help_text=_("File name 'on disk' of the document, e.g. 'gelakt-verslag.pdf'."),
        default="unknown.bin",  # TODO: remove this once we can enforce the blank=False
    )
    bestandsomvang = models.PositiveBigIntegerField(
        _("file size"),
        default=0,
        help_text=_("Size of the file on disk, in bytes."),
    )
    publicatiestatus = models.CharField(
        _("status"),
        max_length=12,
        choices=PublicationStatusOptions.choices,
        default=PublicationStatusOptions.published,
    )
    registratiedatum = models.DateTimeField(
        _("created on"),
        auto_now_add=True,
        editable=False,
        help_text=_(
            "System timestamp reflecting when the document was registered in the "
            "database. Not to be confused with the creation date of the document, "
            "which is usually *before* the registration date."
        ),
    )
    laatst_gewijzigd_datum = models.DateTimeField(
        _("last modified"),
        auto_now=True,
        editable=False,
        help_text=_(
            "System timestamp reflecting when the document was last modified in the "
            "database."
        ),
    )

    # documenthandeling fields
    soort_handeling = models.CharField(
        verbose_name=_("action type"),
        choices=DocumentActionTypeOptions.choices,
        default=DocumentActionTypeOptions.declared,
    )

    # Documents API integration
    document_service = models.ForeignKey(
        "zgw_consumers.Service",
        verbose_name=_("Documents API Service"),
        on_delete=models.PROTECT,
        limit_choices_to={
            "api_type": APITypes.drc,
        },
        null=True,
        blank=True,
    )
    document_uuid = models.UUIDField(
        _("document UUID"),
        help_text=_("The UUID of the API resource recorded in the Documenten API."),
        unique=False,
        editable=True,
        null=True,
        blank=True,
    )
    lock = models.CharField(
        _("document lock"),
        max_length=255,
        blank=True,
        help_text=_(
            "The lock value to be able to update this document in the Documents API.",
        ),
    )
    upload_complete = models.BooleanField(
        _("upload completed"),
        default=False,
        help_text=_(
            "Marker to indicate if the upload to the Documenten API is finalized."
        ),
    )

    # Private property managed by the getter and setter below.
    _zgw_document: ZGWDocument | None = None

    class Meta:  # pyright: ignore
        verbose_name = _("document")
        verbose_name_plural = _("documents")
        constraints = [
            models.CheckConstraint(
                check=(_DOCUMENT_NOT_SET | _DOCUMENT_SET),
                name="documents_api_reference",
                violation_error_message=_(
                    "You must specify both the Documents API service and document UUID to identify a "
                    "document.",
                ),
            )
        ]

    def __str__(self):
        return self.officiele_titel

    def clean(self):
        super().clean()
        if not self.pk and self.publicatiestatus == PublicationStatusOptions.revoked:
            raise ValidationError(
                _("You cannot create a {revoked} document.").format(
                    revoked=PublicationStatusOptions.revoked.label.lower()
                )
            )

    @property
    def documenthandelingen(self) -> DocumentActions:
        """
        Fake documenthandeling field to populate the `DocumentActionSerializer`.
        """
        return [
            {
                "soort_handeling": self.soort_handeling,
                "identifier": DOCUMENT_ACTION_TOOI_IDENTIFIERS[self.soort_handeling],
                "at_time": self.registratiedatum,
                "was_assciated_with": (
                    self.publicatie.verantwoordelijke.uuid
                    if self.publicatie.verantwoordelijke
                    else None
                ),
            }
        ]

    @documenthandelingen.setter
    def documenthandelingen(self, value: DocumentActions) -> None:
        """
        Set the (created) `soort_handeling` field
        """
        assert len(value) == 1
        documenthandeling = value[0]
        assert documenthandeling["soort_handeling"]

        self.soort_handeling = documenthandeling["soort_handeling"]

    @property
    def zgw_document(self) -> ZGWDocument | None:
        """
        The related ZGW Documents API document.

        The created or retrieved ZGW Document, based on the ``document_service`` and
        ``document_uuid`` fields.
        """
        if self._zgw_document:
            return self._zgw_document

        # if we don't have a pointer, do nothing
        if not (self.document_service and self.document_uuid):
            return None

        # at this time we do not dynamically look up the object in the upstream API,
        # since evaluating this property in API detail/list responses adds significant
        # overhead.
        return None

    @zgw_document.setter
    def zgw_document(self, document: ZGWDocument) -> None:
        """
        Set the (created) ZGWDocument in the cache.
        """
        self._zgw_document = document

    def absolute_document_download_uri(self, request: HttpRequest) -> str:
        """
        Creates the absolute document URI for the document-download endpoint.
        """
        return reverse(
            "api:document-download", kwargs={"uuid": str(self.uuid)}, request=request
        )

    @transaction.atomic()
    def register_in_documents_api(
        self,
        build_absolute_uri: Callable[[str], str],
    ) -> None:
        """
        Create the matching document in the Documents API and store the references.

        As a side-effect, this populates ``self.zgw_document``.
        """

        # Look up which service to use to register the document
        config = GlobalConfiguration.get_solo()
        if (service := config.documents_api_service) is None:
            raise RuntimeError(
                "No documents API configured yet! Set up the global configuration."
            )

        # Resolve the 'informatieobjecttype' for the Documents API to use.
        # XXX: if there are multiple, which to pick?
        information_category = self.publicatie.informatie_categorieen.first()
        assert isinstance(information_category, InformationCategory)
        iot_path = reverse(
            "catalogi-informatieobjecttypen-detail",
            kwargs={"uuid": information_category.uuid},
        )
        documenttype_url = build_absolute_uri(iot_path)

        with get_client(service) as client:
            zgw_document = client.create_document(
                # woo_document.identifier will have duplicates
                identification=str(self.uuid),
                source_organisation=config.organisation_rsin,
                document_type_url=documenttype_url,
                creation_date=self.creatiedatum,
                title=self.officiele_titel[:200],
                filesize=self.bestandsomvang,
                filename=self.bestandsnaam,
                author="GPP-Woo/ODRC",  # FIXME
                # content_type=,  # TODO, later
                description=self.omschrijving[:1000],
            )

            # set the URLs for the endpoints. this is not the ideal place to do this,
            # but we need to know the document UUID *and* the part UUID
            for part in zgw_document.file_parts:
                part.url = build_absolute_uri(
                    reverse(
                        "api:document-filepart-detail",
                        kwargs={
                            "uuid": self.uuid,
                            "part_uuid": part.uuid,
                        },
                    )
                )

        # update reference in the database to the created document
        self.document_service = service
        self.document_uuid = zgw_document.uuid
        self.lock = zgw_document.lock
        self.save()

        # cache reference
        self.zgw_document = zgw_document

    def upload_part_data(self, uuid: UUID, file: File) -> bool:
        assert self.document_service, "A Documents API service must be recorded"

        with get_client(self.document_service) as client:
            client.proxy_file_part_upload(
                file,
                file_part_uuid=uuid,
                lock=self.lock,
            )

            completed = client.check_uploads_complete(document_uuid=self.document_uuid)
            if completed:
                client.unlock_document(uuid=self.document_uuid, lock=self.lock)

                self.lock = ""
                self.upload_complete = True
                self.save(update_fields=("lock", "upload_complete"))

        return completed
