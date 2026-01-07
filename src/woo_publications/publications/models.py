from __future__ import annotations

import uuid
from collections.abc import Callable, Collection, Iterator
from copy import copy
from functools import partial
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from dateutil.relativedelta import relativedelta
from django_fsm import (
    ConcurrentTransitionMixin,
    FSMField,
    Transition,
    transition,
)
from rest_framework.reverse import reverse
from typing_extensions import deprecated
from zgw_consumers.constants import APITypes

from woo_publications.accounts.models import User
from woo_publications.config.models import GlobalConfiguration
from woo_publications.constants import ArchiveNominationChoices
from woo_publications.contrib.documents_api.client import (
    Document as ZGWDocument,
    DocumentenClient,
    get_client,
)
from woo_publications.logging.serializing import serialize_instance
from woo_publications.logging.service import (
    audit_admin_update,
    audit_api_update,
)
from woo_publications.logging.typing import ActingUser
from woo_publications.metadata.constants import InformationCategoryOrigins
from woo_publications.metadata.models import InformationCategory
from woo_publications.metadata.service import get_inspannings_verplichting
from woo_publications.utils.validators import (
    max_img_size_validator,
    max_img_width_and_height_validator,
)

from .archiving import get_retention_informatie_category
from .constants import PublicationStatusOptions

# when the document isn't specified both the service and uuid needs to be unset
_DOCUMENT_NOT_SET = models.Q(document_service=None, document_uuid=None)
# when the document is specified both the service and uuid needs to be set
_DOCUMENT_SET = ~models.Q(document_service=None) & ~models.Q(document_uuid=None)

# The method `get_available_publicatiestatus_transitions` is provided by django-fsm
type GetAvailablePublicatiestatusTransitions = Callable[[], Iterator[Transition]]


class Topic(models.Model):
    id: int  # implicitly provided by django
    uuid = models.UUIDField(
        _("UUID"),
        unique=True,
        default=uuid.uuid4,
        editable=False,
    )
    afbeelding = models.ImageField(
        _("Afbeelding"),
        upload_to="topics/",
        validators=[
            FileExtensionValidator(allowed_extensions=settings.ALLOWED_IMG_EXTENSIONS),
            max_img_size_validator,
            max_img_width_and_height_validator,
        ],
    )
    officiele_titel = models.CharField(
        _("official title"),
        max_length=255,
    )
    omschrijving = models.TextField(_("description"), blank=True)
    publicatiestatus = models.CharField(
        _("status"),
        max_length=12,
        choices=PublicationStatusOptions.choices,
        default=PublicationStatusOptions.published,
    )
    promoot = models.BooleanField(
        _("promote"),
        default=False,
        help_text=_(
            "Marker to indicate that this topic will be promoted within the "
            "frontend application."
        ),
    )
    registratiedatum = models.DateTimeField(
        _("created on"),
        auto_now_add=True,
        editable=False,
        help_text=_(
            "System timestamp reflecting when the topic was registered in the database."
        ),
    )
    laatst_gewijzigd_datum = models.DateTimeField(
        _("last modified"),
        auto_now=True,
        editable=False,
        help_text=_(
            "System timestamp reflecting when the topic was last modified in the "
            "database."
        ),
    )

    class Meta:  # pyright: ignore
        verbose_name = _("topic")
        verbose_name_plural = _("topics")

    def __str__(self):
        return self.officiele_titel

    def clean(self):
        super().clean()
        if not self.pk and self.publicatiestatus == PublicationStatusOptions.revoked:
            raise ValidationError(
                _("You cannot create a {revoked} topic.").format(
                    revoked=PublicationStatusOptions.revoked.label.lower()
                )
            )


class Publication(ConcurrentTransitionMixin, models.Model):
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
            "The information categories clarify the kind of information present in "
            "the publication."
        ),
    )
    onderwerpen = models.ManyToManyField(
        Topic,
        verbose_name=_("topics"),
        help_text=_(
            "Topics capture socially relevant information that spans multiple "
            "publications. They can remain relevant for tens of years and exceed the "
            "life span of a single publication."
        ),
        blank=True,
    )
    publisher = models.ForeignKey(
        "metadata.organisation",
        verbose_name=_("publisher"),
        related_name="published_publications",
        help_text=_("The organisation which publishes the publication."),
        limit_choices_to={"is_actief": True},
        on_delete=models.CASCADE,
        # only allow null for concept
        null=True,
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
    eigenaar = models.ForeignKey(
        "accounts.OrganisationMember",
        verbose_name=_("owner"),
        help_text=_(
            "The owner of this publication from gpp-app or gpp-publicatiebank."
        ),
        on_delete=models.PROTECT,
    )
    eigenaar_groep = models.ForeignKey(
        "accounts.OrganisationUnit",
        verbose_name=_("owner (group)"),
        help_text=_(
            "The organisation unit owning this publication, from gpp-app or "
            "gpp-publicatiebank. Any member in the referenced group can manage this "
            "publication."
        ),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
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
    publicatiestatus = FSMField(
        _("status"),
        max_length=12,
        choices=PublicationStatusOptions.choices,
        # protected=True,  TODO - enable in the future?
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
    gepubliceerd_op = models.DateTimeField(
        _("published on"),
        editable=False,
        help_text=_("System timestamp reflecting when the publication was published."),
        null=True,
        blank=True,
    )
    ingetrokken_op = models.DateTimeField(
        _("revoked on"),
        editable=False,
        help_text=_("System timestamp reflecting when the publication was revoked."),
        null=True,
        blank=True,
    )
    datum_begin_geldigheid = models.DateField(
        _("in effect from"),
        help_text=_(
            "The date when the rights and obligations of the attached "
            "documents come into effect."
        ),
        null=True,
        blank=True,
    )
    datum_einde_geldigheid = models.DateField(
        _("in effect until"),
        help_text=_(
            "The date when the rights and obligations of the attached "
            "documents stops being in effect."
        ),
        null=True,
        blank=True,
    )

    # Retention fields:
    bron_bewaartermijn = models.CharField(
        _("retention policy source"),
        help_text=_(
            "The source of the retention policy (example: Selectielijst "
            "gemeenten 2020)."
        ),
        max_length=255,
        blank=True,
    )
    selectiecategorie = models.CharField(
        _("selection category"),
        help_text=_(
            "The category as specified in the provided retention policy source "
            "(example: 20.1.2)."
        ),
        max_length=255,
        blank=True,
    )
    archiefnominatie = models.CharField(
        _("archive action"),
        help_text=_("Determines if the archived data will be retained or disposed."),
        choices=ArchiveNominationChoices.choices,
        max_length=50,
        blank=True,
    )
    archiefactiedatum = models.DateField(
        _("archive action date"),
        help_text=_("Date when the publication will be archived or disposed."),
        null=True,
        blank=True,
    )
    toelichting_bewaartermijn = models.TextField(
        _("retention policy explanation"),
        blank=True,
    )

    get_available_publicatiestatus_transitions: GetAvailablePublicatiestatusTransitions
    publicationidentifier_set: models.QuerySet[PublicationIdentifier]

    class Meta:  # pyright: ignore
        verbose_name = _("publication")
        verbose_name_plural = _("publications")
        constraints = [
            models.CheckConstraint(
                check=(
                    # Not allowed to be null
                    models.Q(publisher__isnull=False)
                    # Allowed to be null
                    | models.Q(publicatiestatus=PublicationStatusOptions.concept)
                    # the admin create action first saves a publication without
                    # publicatiestatus before assigning its status. This is done
                    # so the published method has a pk which is used to trigger
                    # the celery task to index the data and other tasks. This means
                    # that we need to allow the same behavior for concept and "".
                    | models.Q(publicatiestatus="")
                ),
                name="publisher_null_only_for_concept_or_blank",
                violation_error_message=_(
                    "The publisher is only allowed to be unset if the publication "
                    "is a concept."
                ),
            ),
        ]

    def __str__(self):
        return self.officiele_titel

    def save(self, *args, **kwargs):
        if not self.pk:
            assert self.publicatiestatus != PublicationStatusOptions.revoked, (
                "Can't create revoked publications"
            )
        super().save(*args, **kwargs)

    @transition(
        field=publicatiestatus, source="", target=PublicationStatusOptions.concept
    )
    def draft(self) -> None:
        """
        Mark the publication as 'concept'.

        Only freshly created publications can be a draft.
        """
        pass

    @transition(
        field=publicatiestatus,
        # type annotations are missing and pyright infers that only string is allowed
        source=("", PublicationStatusOptions.concept),  # pyright:ignore[reportArgumentType]
        target=PublicationStatusOptions.published,
    )
    def publish(
        self,
        request: HttpRequest,
        user: User | ActingUser,
        remarks: str = "",
    ) -> None:
        """
        Publish the publication.

        Concept and freshly created publications can be published. Publishing triggers
        the publication of all related documents and schedules the index background
        task.
        """
        from .tasks import index_publication

        self.gepubliceerd_op = timezone.now()

        # schedule indexing to the search API
        transaction.on_commit(partial(index_publication.delay, publication_id=self.pk))

        # publish all related documents in the same transaction. All documents must have
        # the concept status at this point, but we err on the side of caution.
        documents: models.QuerySet[Document] = self.document_set.filter(  # pyright: ignore[reportAttributeAccessIssue]
            publicatiestatus=PublicationStatusOptions.concept
        )
        # prepare the condition for the document condition check
        self_copy = copy(self)
        self_copy.publicatiestatus = PublicationStatusOptions.published
        # note that we perform a memory efficient iteration to call the document state
        # transitions, but may spawn a large amount of save/update queries. We can
        # revisit this and complicate the code for performance if we notice performance
        # degradation.
        for document in documents.iterator():
            # update in memory so that the transition condition is satisfied. Note that
            # calling code should make sure to wrap these operations in a transaction!
            document.publicatie = self_copy
            document.publish(request=request)
            document.save()
            document._log_update(user=user, remarks=remarks)

    @transition(
        field=publicatiestatus,
        source=PublicationStatusOptions.published,
        target=PublicationStatusOptions.revoked,
    )
    def revoke(self, user: User | ActingUser, remarks: str = "") -> None:
        """
        Revoke the publication.

        Only published publications can be revoked. Revoking a publication triggers
        revocation of the related documents and schedules a background task to remove
        the publication from the search index.
        """
        from .tasks import remove_publication_from_index

        self.ingetrokken_op = timezone.now()

        # schedule index removal to the search API
        transaction.on_commit(
            partial(remove_publication_from_index.delay, publication_id=self.pk)
        )

        # revoke all related (still published) documents in the same transaction.
        documents = self.document_set.filter(  # pyright: ignore[reportAttributeAccessIssue]
            publicatiestatus=PublicationStatusOptions.published
        )
        # prepare the condition for the document condition check
        self_copy = copy(self)
        self_copy.publicatiestatus = PublicationStatusOptions.revoked
        # note that we perform a memory efficient iteration to call the document state
        # transitions, but may spawn a large amount of save/update queries. We can
        # revisit this and complicate the code for performance if we notice performance
        # degradation.
        for document in documents.iterator():
            # update in memory so that the transition condition is satisfied. Note that
            # calling code should make sure to wrap these operations in a transaction!
            document.publicatie = self_copy
            document.revoke()
            document.save()
            document._log_update(user=user, remarks=remarks)

    @deprecated("To be replaced with explicit .revoke() call")
    def revoke_own_documents(
        self, user: User | ActingUser, remarks: str | None = None
    ) -> None:
        from .tasks import remove_document_from_index

        documents = self.document_set.filter(  # pyright: ignore[reportAttributeAccessIssue]
            models.Q(publicatiestatus=PublicationStatusOptions.concept)
            | models.Q(publicatiestatus=PublicationStatusOptions.published)
        )

        # get a list of IDs of published/concept documents, make sure to evaluate the
        # queryset so it's not affected by the `update` query
        document_ids_to_log = list(documents.values_list("pk", flat=True))
        for document_id in document_ids_to_log:
            transaction.on_commit(
                partial(remove_document_from_index.delay, document_id=document_id)
            )

        documents.update(
            publicatiestatus=PublicationStatusOptions.revoked,
            laatst_gewijzigd_datum=timezone.now(),
            ingetrokken_op=timezone.now(),
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

    def apply_retention_policy(self, commit=True):
        if (
            self.publicatiestatus == PublicationStatusOptions.concept
            or self.publicatiestatus == ""
        ):
            return

        information_category = get_retention_informatie_category(
            self.informatie_categorieen.all()
        )
        assert information_category is not None, (
            "A publication must have at least one information category"
        )
        self.bron_bewaartermijn = information_category.bron_bewaartermijn
        self.selectiecategorie = information_category.selectiecategorie
        self.archiefnominatie = information_category.archiefnominatie
        self.archiefactiedatum = localdate(
            self.gepubliceerd_op
            + relativedelta(years=information_category.bewaartermijn)
        )
        self.toelichting_bewaartermijn = information_category.toelichting_bewaartermijn

        if commit:
            self.save()

    def update_documents_rsin(self):
        from .tasks import update_document_rsin

        config = GlobalConfiguration.get_solo()
        rsin = config.organisation_rsin
        if (publisher := self.publisher) and publisher.rsin:
            rsin = publisher.rsin

        for document in self.document_set.iterator():  # pyright: ignore[reportAttributeAccessIssue]
            transaction.on_commit(
                partial(update_document_rsin.delay, document_id=document.pk, rsin=rsin)
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

    @cached_property
    def gpp_app_url(self) -> str:
        global_config = GlobalConfiguration.get_solo()
        url_template = global_config.gpp_app_publication_url_template
        return url_template.replace("<UUID>", str(self.uuid))

    @cached_property
    def gpp_burgerportaal_url(self) -> str:
        global_config = GlobalConfiguration.get_solo()
        url_template = global_config.gpp_burgerportaal_publication_url_template
        return url_template.replace("<UUID>", str(self.uuid))


class PublicationIdentifier(models.Model):
    id: int  # implicitly provided by django
    publicatie = models.ForeignKey(
        Publication,
        verbose_name=_("publication"),
        help_text=_("The publication that this identifier identifies."),
        on_delete=models.CASCADE,
    )
    kenmerk = models.CharField(
        _("identifier"),
        max_length=40,
        help_text=_(
            "The identifier that (combined with bron) uniquely identifies the "
            "publication."
        ),
    )
    bron = models.CharField(
        _("source"),
        max_length=40,
        help_text=_("Determines where the identifier is defined and sourced from."),
    )

    class Meta:
        verbose_name = pgettext_lazy("trait", "identifier")
        verbose_name_plural = pgettext_lazy("trait", "identifiers")
        constraints = [
            models.UniqueConstraint(
                fields=["publicatie", "kenmerk", "bron"],
                name="no_duplicate_publication_identifiers",
            )
        ]

    def __str__(self):
        return f"{self.bron}: {self.kenmerk}"


class PublicatieStatusMatch:
    def __init__(self, expected: Collection[PublicationStatusOptions]):
        self.expected = expected

    def __call__(self, instance: Document) -> bool:
        # if there's no related publication, we can't do anything
        try:
            publication: Publication = instance.publicatie
        except Publication.DoesNotExist:
            return False
        return publication.publicatiestatus in self.expected


class Document(ConcurrentTransitionMixin, models.Model):
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
    eigenaar = models.ForeignKey(
        "accounts.OrganisationMember",
        verbose_name=_("owner"),
        help_text=_("The owner of this document from gpp-app or gpp-publicatiebank."),
        on_delete=models.PROTECT,
    )
    # TODO: remove this field in future release because it is deprecated
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
    source_url = models.URLField(
        _("source URL"),
        max_length=1000,
        blank=True,
        help_text=_(
            "If the document originates from a Documenten API, this URL uniquely "
            "identifies the matching resource. The value is empty for manual uploads."
        ),
    )
    publicatiestatus = FSMField(
        _("status"),
        max_length=12,
        choices=PublicationStatusOptions.choices,
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
    ontvangstdatum = models.DateTimeField(
        _("date of reception"),
        help_text=_("The timestamp when the document is received by the organisatie."),
        null=True,
        blank=True,
    )
    datum_ondertekend = models.DateTimeField(
        _("signed date"),
        help_text=_("The timestamp when the document is signed by the organisatie."),
        null=True,
        blank=True,
    )
    gepubliceerd_op = models.DateTimeField(
        _("published on"),
        editable=False,
        help_text=_("System timestamp reflecting when the publication was published."),
        null=True,
        blank=True,
    )
    ingetrokken_op = models.DateTimeField(
        _("revoked on"),
        editable=False,
        help_text=_("System timestamp reflecting when the publication was revoked."),
        null=True,
        blank=True,
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

    get_publicatiestatus_display: Callable[[], str]
    get_available_publicatiestatus_transitions: GetAvailablePublicatiestatusTransitions
    documentidentifier_set: models.QuerySet[DocumentIdentifier]

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
                    "You must specify both the Documents API service and document UUID "
                    "to identify a document.",
                ),
            )
        ]

    def __str__(self):
        return self.officiele_titel

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

    @transition(
        field=publicatiestatus,
        source="",
        target=PublicationStatusOptions.concept,
        conditions=(PublicatieStatusMatch({PublicationStatusOptions.concept}),),
    )
    def draft(self) -> None:
        """
        Mark the document as 'concept'.

        Draft documents can only occur within draft publications.
        """
        pass  # pragma: no cover

    @transition(
        field=publicatiestatus,
        source=("", PublicationStatusOptions.concept),  # pyright:ignore[reportArgumentType]
        target=PublicationStatusOptions.published,
        conditions=(PublicatieStatusMatch({PublicationStatusOptions.published}),),
    )
    def publish(self, request: HttpRequest) -> None:
        """
        Publish the document.

        A published document can only occur within a published publication. Publish the
        publication to trigger the publication of the documents. When a document is
        published, it's sent to the search API for indexing.

        Publication events are logged to the audit log.
        """
        from .tasks import index_document

        self.gepubliceerd_op = timezone.now()

        # schedule indexing to the search API
        download_url = self.absolute_document_download_uri(request=request)
        transaction.on_commit(
            partial(
                index_document.delay, document_id=self.pk, download_url=download_url
            )
        )

    @transition(
        field=publicatiestatus,
        source=PublicationStatusOptions.published,
        target=PublicationStatusOptions.revoked,
        conditions=(
            PublicatieStatusMatch(
                {
                    PublicationStatusOptions.published,
                    PublicationStatusOptions.revoked,
                }
            ),
        ),
    )
    def revoke(self) -> None:
        """
        Revoke the document.

        Revoked documents can occur within published and revoked publications. When a
        publication is revoked, all its documents will be revoked automatically. A
        document can also be revoked individually.

        Revocation sends an update to the search API to remove it from the index.
        """
        from .tasks import remove_document_from_index

        self.ingetrokken_op = timezone.now()

        transaction.on_commit(
            partial(remove_document_from_index.delay, document_id=self.pk)
        )

    def _log_update(self, user: User | ActingUser, remarks: str = "") -> None:
        # audit log the publication event
        serialized = serialize_instance(self)
        if isinstance(user, User):
            audit_admin_update(
                content_object=self,
                object_data=serialized,
                django_user=user,
            )
        else:
            audit_api_update(
                content_object=self,
                object_data=serialized,
                user_id=str(user["identifier"]),
                user_display=user["display_name"],
                remarks=remarks,
            )

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

        from woo_publications.contrib.documents_api.api import DUMMY_IC_UUID

        # Look up which service to use to register the document
        config = GlobalConfiguration.get_solo()
        if (service := config.documents_api_service) is None:
            raise RuntimeError(
                "No documents API configured yet! Set up the global configuration."
            )

        # Resolve the 'informatieobjecttype' for the Documents API to use.
        # XXX: if there are multiple, which to pick?
        information_category = self.publicatie.informatie_categorieen.first()
        if not information_category:
            # Now that IC's can be empty because of concept publications.
            # Assign the hardcoded dummy information category for the generation
            # of the document_type_url.
            information_category = InformationCategory(uuid=DUMMY_IC_UUID)

        assert isinstance(information_category, InformationCategory)
        iot_path = reverse(
            "catalogi-informatieobjecttypen-detail",
            kwargs={"uuid": information_category.uuid},
        )
        documenttype_url = build_absolute_uri(iot_path)

        rsin = config.organisation_rsin
        if (publisher := self.publicatie.publisher) and publisher.rsin:
            rsin = publisher.rsin

        with get_client(service) as client:
            zgw_document = client.create_document(
                # woo_document.identifier will have duplicates
                identification=str(self.uuid),
                source_organisation=rsin,
                document_type_url=documenttype_url,
                creation_date=self.creatiedatum,
                title=self.officiele_titel[:200],
                filesize=self.bestandsomvang,
                filename=self.bestandsnaam,
                author="GPP-Woo/GPP-publicatiebank",  # FIXME
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

    @transaction.atomic()
    def destroy_document(self) -> None:
        """
        Destroy the matching document in the Documents API.
        And remove the index in the gpp-search component.

        return if the destruction was successful or not.
        """

        from .tasks import remove_document_from_index

        # Always remove from index so the doc isn't publicly available
        # even in the case of errors
        remove_document_from_index.delay(document_id=self.pk)

        # Both should be either set or unset because of the constraint
        # but just to be sure lets check on both.
        if not self.document_service or not self.document_uuid:
            return

        with get_client(self.document_service) as client:
            client.destroy_document(uuid=self.document_uuid)

    def upload_part_data(self, uuid: UUID, file: File) -> bool:
        assert self.document_service, "A Documents API service must be recorded"

        with get_client(self.document_service) as client:
            client.proxy_file_part_upload(
                file,
                file_part_uuid=uuid,
                lock=self.lock,
            )
            completed = self.check_and_mark_completed(client)

        return completed

    def check_and_mark_completed(self, client: DocumentenClient) -> bool:
        completed = client.check_uploads_complete(document_uuid=self.document_uuid)
        if completed:
            client.unlock_document(uuid=self.document_uuid, lock=self.lock)

            self.lock = ""
            self.upload_complete = True
            self.save(update_fields=("lock", "upload_complete"))
        return completed


class DocumentIdentifier(models.Model):
    id: int  # implicitly provided by django
    document = models.ForeignKey(
        Document,
        verbose_name=_("document"),
        help_text=_("The document that this identifier identifies."),
        on_delete=models.CASCADE,
    )
    kenmerk = models.CharField(
        _("identifier"),
        max_length=40,
        help_text=_(
            "The identifier that (combined with bron) uniquely identifies the document."
        ),
    )
    bron = models.CharField(
        _("source"),
        max_length=40,
        help_text=_("Determines where the identifier is defined and sourced from."),
    )

    class Meta:
        verbose_name = pgettext_lazy("trait", "identifier")
        verbose_name_plural = pgettext_lazy("trait", "identifiers")
        constraints = [
            models.UniqueConstraint(
                fields=["document", "kenmerk", "bron"],
                name="no_duplicate_document_identifiers",
            )
        ]

    def __str__(self):
        return f"{self.bron}: {self.kenmerk}"
