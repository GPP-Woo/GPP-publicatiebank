from collections.abc import Sequence
from functools import partial

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import structlog
from django_fsm import FSMField
from drf_polymorphic.serializers import PolymorphicSerializer
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers
from rest_framework.request import Request

from woo_publications.accounts.models import OrganisationMember
from woo_publications.contrib.documents_api.client import FilePart

from ...constants import DocumentDeliveryMethods, PublicationStatusOptions
from ...models import (
    Document,
    DocumentIdentifier,
    Publication,
)
from ...tasks import index_document
from ...typing import Kenmerk
from ..utils import _get_fsm_help_text
from ..validators import (
    PublicationStatusValidator,
    SourceDocumentURLValidator,
    validate_duplicated_kenmerken,
)
from .owner import EigenaarSerializer, update_or_create_organisation_member

logger = structlog.stdlib.get_logger(__name__)


class FilePartSerializer(serializers.Serializer[FilePart]):
    uuid = serializers.UUIDField(
        label=_("UUID"),
        help_text=_("The unique ID for a given file part for a document."),
        read_only=True,
    )
    url = serializers.URLField(
        label=_("url"),
        help_text=_("Endpoint where to submit the file part data to."),
        read_only=True,
    )
    volgnummer = serializers.IntegerField(
        source="order",
        label=_("order"),
        help_text=_("Index of the filepart, indicating which chunk is being uploaded."),
        read_only=True,
    )
    omvang = serializers.IntegerField(
        source="size",
        label=_("size"),
        help_text=_(
            "Chunk size, in bytes. Large files must be cut up into chunks, where each "
            "chunk has an expected chunk size (configured on the Documents API "
            "server). A part is only considered complete once each chunk has binary "
            "data of exactly this size attached to it."
        ),
        read_only=True,
    )
    inhoud = serializers.FileField(
        label=_("binary content"),
        help_text=_(
            "The binary data of this chunk, which will be forwarded to the underlying "
            "Documents API. The file size must match the part's `omvang`."
        ),
        write_only=True,
        use_url=False,
    )


class DocumentStatusSerializer(serializers.Serializer):
    document_upload_voltooid = serializers.BooleanField(
        label=_("document upload completed"),
        help_text=_(
            "Indicates if all chunks of the file have been received and the document "
            "has been unlocked and made 'ready for use' in the upstream Documents API."
        ),
    )


class DocumentIdentifierSerializer(serializers.ModelSerializer[DocumentIdentifier]):
    class Meta:  # pyright: ignore
        model = DocumentIdentifier
        fields = (
            "kenmerk",
            "bron",
        )


@extend_schema_serializer(deprecate_fields=("identifier",))
class DocumentSerializer(serializers.ModelSerializer[Document]):
    publicatie = serializers.SlugRelatedField(
        queryset=Publication.objects.all(),
        slug_field="uuid",
        help_text=_("The unique identifier of the publication."),
    )
    eigenaar = EigenaarSerializer(
        label=_("owner"),
        help_text=_(
            "The creator of the document, derived from the audit headers.\n"
            "Disclaimer**: If you use this field during creation/updating actions the "
            "owner data will differ from the audit headers provided during creation."
        ),
        allow_null=True,
        required=False,
    )
    kenmerken = DocumentIdentifierSerializer(
        help_text=_("The document identifiers attached to this document."),
        many=True,
        source="documentidentifier_set",
        required=False,
    )
    upload_voltooid = serializers.BooleanField(
        source="upload_complete",
        read_only=True,
        label=_("document upload completed"),
        help_text=_(
            "Indicates if the file has been uploaded and made 'ready for use' in the "
            "upstream Documents API."
        ),
    )

    class Meta:  # pyright: ignore
        model = Document
        fields = (
            "uuid",
            "identifier",
            "publicatie",
            "kenmerken",
            "officiele_titel",
            "verkorte_titel",
            "omschrijving",
            "publicatiestatus",
            "gepubliceerd_op",
            "ingetrokken_op",
            "creatiedatum",
            "ontvangstdatum",
            "datum_ondertekend",
            "bestandsformaat",
            "bestandsnaam",
            "bestandsomvang",
            "eigenaar",
            "registratiedatum",
            "laatst_gewijzigd_datum",
            "upload_voltooid",
        )
        extra_kwargs = {
            "uuid": {
                "read_only": True,
            },
            "publicatiestatus": {
                # read-only unless it's an update, see DocumentUpdateSerializer below
                "read_only": True,
                "validators": [PublicationStatusValidator()],
                "help_text": _(
                    "\nOn creation, the publicatiestatus is derived from the "
                    "publication and cannot be specified directly."
                ),
            },
        }

    def get_fields(self):
        fields = super().get_fields()
        assert fields["publicatiestatus"].help_text
        fsm_field = Document._meta.get_field("publicatiestatus")
        assert isinstance(fsm_field, FSMField)
        fields["publicatiestatus"].help_text += _get_fsm_help_text(fsm_field)
        return fields

    def validate_kenmerken(self, value: Sequence[Kenmerk]) -> Sequence[Kenmerk]:
        validate_duplicated_kenmerken(value)
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        instance = self.instance
        assert isinstance(instance, Document | None)

        # publicatie can be absent for partial updates
        publication: Publication
        match (instance, self.partial):
            # create
            case None, False:
                publication = attrs["publicatie"]
                # Adding new documents to revoked publications is forbidden.
                if publication.publicatiestatus == PublicationStatusOptions.revoked:
                    raise serializers.ValidationError(
                        _("Adding documents to revoked publications is not allowed."),
                        code="publication_revoked",
                    )
            # (partial) update
            case Document(), bool():
                publication = attrs.get("publicatie", instance.publicatie)
            case _:  # pragma: no cover
                raise AssertionError("unreachable code")

        return attrs


class RetrieveUrlDocumentCreateSerializer(serializers.ModelSerializer):
    document_url = serializers.URLField(
        source="source_url",
        label=_("document URL"),
        required=True,
        allow_blank=False,
        help_text=_(
            "The resource URL of the document in an (external) Documents API. Must be "
            "the detail endpoint - we'll construct the download URL ourselves. Must be "
            "provided when the `aanleveringBestand` is set to `ophalen`, and must be "
            "empty/absent when `aanleveringBestand` is `ontvangen`. Note that you may "
            "include the `versie` query parameter to point to a particular document "
            "version."
        ),
        validators=[SourceDocumentURLValidator()],
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = Document
        fields = ("document_url",)


class DocumentCreateSerializer(PolymorphicSerializer, DocumentSerializer):
    """
    Manage the creation of new Documents.
    """

    aanlevering_bestand = serializers.ChoiceField(
        label=_("delivery method"),
        choices=DocumentDeliveryMethods.choices,
        default=DocumentDeliveryMethods.receive_upload,
        help_text=_(
            "When the delivery method is set to retrieve a provided document "
            "URL pointing to a Documents API, then this will be processed in the "
            "background and no `bestandsdelen` will be returned. Otherwise for "
            "direct uploads, an array of expected file parts is returned."
        ),
    )
    bestandsdelen = FilePartSerializer(
        label=_("file parts"),
        help_text=_(
            "The expected file parts/chunks to upload the file contents. These are "
            "derived from the specified total file size (`bestandsomvang`) in the "
            "document create body."
        ),
        source="zgw_document.file_parts",
        many=True,
        read_only=True,
        allow_null=True,
    )

    discriminator_field = "aanlevering_bestand"
    serializer_mapping = {
        DocumentDeliveryMethods.receive_upload.value: None,
        DocumentDeliveryMethods.retrieve_url.value: RetrieveUrlDocumentCreateSerializer,
    }

    class Meta(DocumentSerializer.Meta):
        fields = DocumentSerializer.Meta.fields + (
            "aanlevering_bestand",
            "bestandsdelen",
        )

    @transaction.atomic
    def create(self, validated_data):
        # not a model field, drop it. This is used for validation to check source_url.
        validated_data.pop("aanlevering_bestand")
        document_identifiers = validated_data.pop("documentidentifier_set", [])
        # on create, the status is always derived from the publication. Anything
        # submitted by the client is ignored.
        publication: Publication = validated_data["publicatie"]
        validated_data["publicatiestatus"] = publication.publicatiestatus

        validated_data["eigenaar"] = update_or_create_organisation_member(
            self.context["request"], validated_data.get("eigenaar")
        )

        if validated_data["publicatiestatus"] == PublicationStatusOptions.published:
            validated_data["gepubliceerd_op"] = timezone.now()

        document = super().create(validated_data)

        DocumentIdentifier.objects.bulk_create(
            DocumentIdentifier(document=document, **identifiers)
            for identifiers in document_identifiers
        )

        return document


class DocumentUpdateSerializer(DocumentSerializer):
    """
    Manage updates to metadata of Documents.
    """

    publicatie = serializers.SlugRelatedField(
        slug_field="uuid",
        help_text=_("The unique identifier of the publication."),
        read_only=True,
    )

    class Meta(DocumentSerializer.Meta):
        fields = DocumentSerializer.Meta.fields
        read_only_fields = [
            field
            for field in DocumentSerializer.Meta.fields
            if field
            not in (
                "officiele_titel",
                "verkorte_titel",
                "omschrijving",
                "publicatiestatus",
                "eigenaar",
                "creatiedatum",
                "ontvangstdatum",
                "datum_ondertekend",
            )
        ]
        extra_kwargs = {
            "officiele_titel": {
                "required": False,
            },
            "creatiedatum": {
                "required": False,
            },
            "publicatiestatus": {
                **DocumentSerializer.Meta.extra_kwargs["publicatiestatus"],
                "read_only": False,
            },
        }

    @transaction.atomic
    def update(self, instance, validated_data):
        update_document_identifiers = "documentidentifier_set" in validated_data
        document_identifiers = validated_data.pop("documentidentifier_set", [])

        if "eigenaar" in validated_data:
            eigenaar = validated_data.pop("eigenaar")
            validated_data["eigenaar"] = OrganisationMember.objects.get_and_sync(
                identifier=eigenaar["identifier"], naam=eigenaar["naam"]
            )

        # pop the target state from the validate data to avoid setting it directly,
        # instead apply the state transitions based on old -> new state
        current_publication_status: PublicationStatusOptions = instance.publicatiestatus
        new_publication_status: PublicationStatusOptions = validated_data.pop(
            "publicatiestatus",
            current_publication_status,
        )

        match (current_publication_status, new_publication_status):
            case (PublicationStatusOptions.published, PublicationStatusOptions.revoked):
                instance.revoke()
            case _:
                request: Request = self.context["request"]
                # ensure that the search index is updated - revoke state transitions
                # call these tasks themselves
                download_url = instance.absolute_document_download_uri(request)
                transaction.on_commit(
                    partial(
                        index_document.delay,
                        document_id=instance.pk,
                        download_url=download_url,
                    )
                )

                logger.debug(
                    "state_transition_skipped",
                    source_status=current_publication_status,
                    target_status=new_publication_status,
                    model=instance._meta.model_name,
                    pk=instance.pk,
                )

        document = super().update(instance, validated_data)

        if update_document_identifiers:
            document.documentidentifier_set.all().delete()  # pyright: ignore[reportAttributeAccessIssue]
            DocumentIdentifier.objects.bulk_create(
                DocumentIdentifier(document=document, **identifiers)
                for identifiers in document_identifiers
            )

        return document
