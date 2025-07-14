from collections.abc import Sequence
from functools import partial
from typing import Literal, TypedDict

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import structlog
from django_fsm import FSMField
from drf_polymorphic.serializers import PolymorphicSerializer
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field, extend_schema_serializer
from rest_framework import serializers
from rest_framework.request import Request

from woo_publications.accounts.models import OrganisationMember
from woo_publications.api.drf_spectacular.headers import (
    AUDIT_USER_ID_PARAMETER,
    AUDIT_USER_REPRESENTATION_PARAMETER,
)
from woo_publications.contrib.documents_api.client import FilePart
from woo_publications.logging.api_tools import extract_audit_parameters
from woo_publications.metadata.models import InformationCategory, Organisation

from ..constants import DocumentDeliveryMethods, PublicationStatusOptions
from ..models import (
    Document,
    DocumentIdentifier,
    Publication,
    PublicationIdentifier,
    Topic,
)
from ..tasks import index_document, index_publication
from ..typing import Kenmerk
from .utils import _get_fsm_help_text
from .validators import PublicationStatusValidator, SourceDocumentURLValidator

logger = structlog.stdlib.get_logger(__name__)


class OwnerData(TypedDict):
    naam: str
    identifier: str


def update_or_create_organisation_member(
    request: HttpRequest, details: OwnerData | None = None
):
    if details is None:
        details = {
            "identifier": request.headers[AUDIT_USER_ID_PARAMETER.name],
            "naam": request.headers[AUDIT_USER_REPRESENTATION_PARAMETER.name],
        }
    return OrganisationMember.objects.get_and_sync(**details)


def _has_duplicate_nested_serializer_items(value):
    # transforms the nested dicts into a set and checks if the length is the same as
    # the original passed data. If the length is different that means that there were
    # duplicated items present because sets can't contain duplicate items.
    if (unique_value := {tuple(identifier.items()) for identifier in value}) and len(
        unique_value
    ) != len(value):
        return True

    return False


class EigenaarSerializer(serializers.ModelSerializer[OrganisationMember]):
    weergave_naam = serializers.CharField(
        source="naam",
        help_text=_("The display name of the user."),
    )

    class Meta:  # pyright: ignore
        model = OrganisationMember
        fields = (
            "identifier",
            "weergave_naam",
        )
        # Removed the none basic validators which are getting in the way for
        # update_or_create
        extra_kwargs = {"identifier": {"validators": []}}

    def validate(self, attrs):
        has_naam = bool(attrs.get("naam"))
        has_identifier = bool(attrs.get("identifier"))

        # added custom validator to check if both are present or not in case
        if has_naam != has_identifier:
            raise serializers.ValidationError(
                _(
                    "The fields 'naam' and 'weergaveNaam' has to be both "
                    "present or excluded."
                )
            )

        return super().validate(attrs)


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

    def validate_kenmerken(self, value: list[Kenmerk]):
        # Assert that there weren't any duplicated items given by the user.
        if value and _has_duplicate_nested_serializer_items(value):
            raise serializers.ValidationError(
                _("You cannot provide identical identifiers.")
            )

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


class PublicationIdentifierSerializer(
    serializers.ModelSerializer[PublicationIdentifier]
):
    class Meta:  # pyright: ignore
        model = PublicationIdentifier
        fields = (
            "kenmerk",
            "bron",
        )


class PublicationSerializer(serializers.ModelSerializer[Publication]):
    """
    Base serializer for publication read and write operations.

    This base class defines the shared logic that should be kept in sync between read
    and write operations for consistent API documentation (and behaviour).
    """

    url_publicatie_intern = serializers.SerializerMethodField(
        label=_("internal publication url"),
        help_text=_(
            "URL to the UI of the internal application where the publication life "
            "cycle is managed. Requires the global configuration parameter to be set, "
            "otherwise an empty string is returned."
        ),
    )
    url_publicatie_extern = serializers.SerializerMethodField(
        label=_("external publication url"),
        help_text=_(
            "URL to the UI of the external application where the publication life "
            "cycle is managed. Requires the global configuration parameter to be set, "
            "otherwise an empty string is returned."
        ),
    )
    informatie_categorieen = serializers.SlugRelatedField(
        queryset=InformationCategory.objects.all(),
        slug_field="uuid",
        help_text=_(
            "The information categories clarify the kind of information present in "
            "the publication."
        ),
        many=True,
        required=True,
        allow_empty=False,
    )
    di_woo_informatie_categorieen = serializers.ListField(
        child=serializers.UUIDField(),
        source="get_diwoo_informatie_categorieen_uuids",
        help_text=_("The information categories used for the sitemap"),
        read_only=True,
    )
    onderwerpen = serializers.SlugRelatedField(
        queryset=Topic.objects.all(),
        slug_field="uuid",
        help_text=_(
            "Topics capture socially relevant information that spans multiple "
            "publications. They can remain relevant for tens of years and exceed the "
            "life span of a single publication."
        ),
        many=True,
        allow_empty=True,
        required=False,
    )
    publisher = serializers.SlugRelatedField(
        queryset=Organisation.objects.filter(is_actief=True),
        slug_field="uuid",
        help_text=_("The organisation which publishes the publication."),
        many=False,
    )
    verantwoordelijke = serializers.SlugRelatedField(
        queryset=Organisation.objects.filter(is_actief=True),
        slug_field="uuid",
        help_text=_(
            "The organisation which is liable for the publication and its contents."
        ),
        many=False,
        allow_null=True,
        required=False,
    )
    opsteller = serializers.SlugRelatedField(
        queryset=Organisation.objects.all(),
        slug_field="uuid",
        help_text=_("The organisation which drafted the publication and its content."),
        many=False,
        allow_null=True,
        required=False,
    )
    kenmerken = PublicationIdentifierSerializer(
        help_text=_("The publication identifiers attached to this publication."),
        many=True,
        source="publicationidentifier_set",
        required=False,
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

    class Meta:  # pyright: ignore
        model = Publication
        fields = (
            "uuid",
            "url_publicatie_intern",
            "url_publicatie_extern",
            "informatie_categorieen",
            "di_woo_informatie_categorieen",
            "onderwerpen",
            "publisher",
            "verantwoordelijke",
            "opsteller",
            "kenmerken",
            "officiele_titel",
            "verkorte_titel",
            "omschrijving",
            "eigenaar",
            "publicatiestatus",
            "gepubliceerd_op",
            "ingetrokken_op",
            "registratiedatum",
            "laatst_gewijzigd_datum",
            "datum_begin_geldigheid",
            "datum_einde_geldigheid",
            "bron_bewaartermijn",
            "selectiecategorie",
            "archiefnominatie",
            "archiefactiedatum",
            "toelichting_bewaartermijn",
        )
        extra_kwargs = {
            "uuid": {"read_only": True},
            "registratiedatum": {"read_only": True},
            "laatst_gewijzigd_datum": {"read_only": True},
            "publicatiestatus": {
                "help_text": _(
                    "\n**Disclaimer**: you can't create a {revoked} publication."
                    "\n\n**Disclaimer**: when you revoke a publication, the attached "
                    "published documents also get revoked."
                ).format(
                    revoked=PublicationStatusOptions.revoked.label.lower(),
                ),
                "required": False,
                "default": PublicationStatusOptions.published,
                "validators": [PublicationStatusValidator()],
            },
            "bron_bewaartermijn": {
                "help_text": _(
                    "The source of the retention policy (example: Selectielijst "
                    "gemeenten 2020)."
                    "\n\n**Note** on create or when updating the information "
                    "categories, manually provided values are ignored and overwritten "
                    "by the automatically derived parameters from the related "
                    "information categories."
                )
            },
            "selectiecategorie": {
                "help_text": _(
                    "The category as specified in the provided retention policy source "
                    "(example: 20.1.2)."
                    "\n\n**Note** on create or when updating the information "
                    "categories, manually provided values are ignored and overwritten "
                    "by the automatically derived parameters from the related "
                    "information categories."
                )
            },
            "archiefnominatie": {
                "help_text": _(
                    "Determines if the archived data will be retained or destroyed."
                    "\n\n**Note** on create or when updating the information "
                    "categories, manually provided values are ignored and overwritten "
                    "by the automatically derived parameters from the related "
                    "information categories."
                )
            },
            "archiefactiedatum": {
                "help_text": _(
                    "Date when the publication will be archived or destroyed."
                    "\n\n**Note** on create or when updating the information "
                    "categories, manually provided values are ignored and overwritten "
                    "by the automatically derived parameters from the related "
                    "information categories."
                )
            },
            "toelichting_bewaartermijn": {
                "help_text": _(
                    "**Note** on create or when updating the information "
                    "categories, manually provided values are ignored and overwritten "
                    "by the automatically derived parameters from the related "
                    "information categories."
                )
            },
        }

    def get_fields(self):
        fields = super().get_fields()
        # When the given status (with fall back on the set data) is concept
        # Then make all fields optional.
        if hasattr(self, "initial_data"):
            publicatiestatus = self.initial_data.get("publicatiestatus")
            # When publicatiestatus isn't given ensure that the default value is used
            # unless it is a partial update, in that case use the instance.
            if not publicatiestatus:
                if self.partial:
                    assert isinstance(self.instance, Publication)
                    publicatiestatus = self.instance.publicatiestatus
                else:
                    publicatiestatus = fields["publicatiestatus"].default

            if publicatiestatus == PublicationStatusOptions.concept:
                for field in fields:
                    # Ensure that officiele_titel remains required.
                    if field != "officiele_titel":
                        fields[field].required = False
                        fields[field].allow_null = True
                        fields[field].allow_empty = True  # pyright: ignore[reportAttributeAccessIssue]

        assert fields["publicatiestatus"].help_text
        fsm_field = Publication._meta.get_field("publicatiestatus")
        assert isinstance(fsm_field, FSMField)
        fields["publicatiestatus"].help_text += _get_fsm_help_text(fsm_field)
        return fields

    def to_internal_value(self, data):
        publicatiestatus = data.get("publicatiestatus")
        # When publicatiestatus isn't given ensure that the default value is used
        # unless it is a partial update, in that case use the instance.
        if not publicatiestatus:
            if self.partial:
                assert isinstance(self.instance, Publication)
                publicatiestatus = self.instance.publicatiestatus
            else:
                publicatiestatus = self.fields["publicatiestatus"].default

        if publicatiestatus == PublicationStatusOptions.concept:
            # Make sure to transform some field to the correct empty value.
            if "informatie_categorieen" in data and not data["informatie_categorieen"]:
                data["informatie_categorieen"] = []

            if "onderwerpen" in data and not data["onderwerpen"]:
                data["onderwerpen"] = []

            if "kenmerken" in data and not data["kenmerken"]:
                data["kenmerken"] = []

        return super().to_internal_value(data)

    @extend_schema_field(OpenApiTypes.URI | Literal[""])  # pyright: ignore[reportArgumentType]
    def get_url_publicatie_intern(self, obj: Publication) -> str:
        return obj.gpp_app_url

    @extend_schema_field(OpenApiTypes.URI | Literal[""])  # pyright: ignore[reportArgumentType]
    def get_url_publicatie_extern(self, obj: Publication) -> str:
        return obj.gpp_burgerportaal_url


class PublicationReadSerializer(PublicationSerializer):
    """
    Encapsulate the read behaviour for publication serialization.

    For read operations, we're much closer to the database model and can provide
    stronger guarantees about the returned data, leading to stricter schema/type
    definitions.
    """

    class Meta(PublicationSerializer.Meta):
        extra_kwargs = {
            **PublicationSerializer.Meta.extra_kwargs,
        }


class PublicationWriteSerializer(PublicationSerializer):
    """
    Encapsulate the create/update validation logic and behaviour.

    The publication serializer is split in read/write parts so that the output can be
    properly documented in the API schema. Writes for concept publications are much
    more relaxed that published publications.

    .. todo:: test validation behaviour of an incomplete concept publication being
    changed to published.
    """

    def validate_kenmerken(self, value: Sequence[Kenmerk]):
        # Assert that there weren't any duplicated items given by the user.
        if value and _has_duplicate_nested_serializer_items(value):
            raise serializers.ValidationError(
                _("You cannot provide identical identifiers.")
            )

        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        instance = self.instance
        assert isinstance(instance, Publication | None)

        # updating revoked publications is not allowed
        if (
            instance is not None
            and instance.publicatiestatus == PublicationStatusOptions.revoked
        ):
            raise serializers.ValidationError(
                _("You cannot modify a {revoked} publication.").format(
                    revoked=PublicationStatusOptions.revoked.label.lower()
                )
            )

        return attrs

    @transaction.atomic
    def update(self, instance: Publication, validated_data):
        apply_retention = False
        reindex_documents = False

        # pop the target state from the validate data to avoid setting it directly,
        # instead apply the state transitions based on old -> new state
        current_publication_status: PublicationStatusOptions = instance.publicatiestatus
        new_publication_status: PublicationStatusOptions = validated_data.pop(
            "publicatiestatus",
            current_publication_status,
        )

        update_publicatie_identifiers = "publicationidentifier_set" in validated_data
        publication_identifiers = validated_data.pop("publicationidentifier_set", [])

        if "eigenaar" in validated_data:
            if eigenaar := validated_data.pop("eigenaar"):
                validated_data["eigenaar"] = OrganisationMember.objects.get_and_sync(
                    identifier=eigenaar["identifier"], naam=eigenaar["naam"]
                )

        request: Request = self.context["request"]
        user_id, user_repr, remarks = extract_audit_parameters(request)

        match (current_publication_status, new_publication_status):
            case (PublicationStatusOptions.concept, PublicationStatusOptions.published):
                instance.publish(
                    request,
                    user={"identifier": user_id, "display_name": user_repr},
                    remarks=remarks,
                )
                apply_retention = True
            case (PublicationStatusOptions.published, PublicationStatusOptions.revoked):
                instance.revoke(
                    user={"identifier": user_id, "display_name": user_repr},
                    remarks=remarks,
                )
            case _:
                # ensure that the search index is updated - publish/revoke state
                # transitions call these tasks themselves
                transaction.on_commit(
                    partial(index_publication.delay, publication_id=instance.pk)
                )
                logger.debug(
                    "state_transition_skipped",
                    source_status=current_publication_status,
                    target_status=new_publication_status,
                    model=instance._meta.model_name,
                    pk=instance.pk,
                )
                # determine if attention_policy should be applied or not.
                if informatie_categorieen := validated_data.get(
                    "informatie_categorieen"
                ):
                    old_informatie_categorieen_set = {
                        ic.uuid for ic in instance.informatie_categorieen.all()
                    }
                    new_informatie_categorieen_set = {
                        ic.uuid for ic in informatie_categorieen
                    }

                    if old_informatie_categorieen_set != new_informatie_categorieen_set:
                        apply_retention = True

                # According ticket #309 the document data must re-index when
                # publication updates `publisher` or `informatie_categorieen`.
                if (
                    "publisher" in validated_data
                    and instance.publisher != validated_data["publisher"]
                ) or (
                    "informatie_categorieen" in validated_data
                    and instance.informatie_categorieen.all()
                    != validated_data["informatie_categorieen"]
                ):
                    reindex_documents = True

        publication = super().update(instance, validated_data)

        if update_publicatie_identifiers:
            publication.publicationidentifier_set.all().delete()  # pyright: ignore[reportAttributeAccessIssue]
            PublicationIdentifier.objects.bulk_create(
                PublicationIdentifier(publicatie=publication, **identifiers)
                for identifiers in publication_identifiers
            )

        if apply_retention:
            publication.apply_retention_policy(commit=True)

        if reindex_documents:
            for document in instance.document_set.iterator():  # pyright: ignore[reportAttributeAccessIssue]
                transaction.on_commit(
                    partial(index_document.delay, document_id=document.pk)
                )

        return publication

    @transaction.atomic
    def create(self, validated_data):
        # pop the target state since we apply it through the transition methods instead
        # of setting it directly. The field default ensures that missing keys get a
        # default and the field disallows the empty string.
        publicatiestatus: PublicationStatusOptions = validated_data.pop(
            "publicatiestatus"
        )
        publication_identifiers = validated_data.pop("publicationidentifier_set", [])

        validated_data["eigenaar"] = update_or_create_organisation_member(
            self.context["request"], validated_data.get("eigenaar")
        )

        publication = super().create(validated_data)

        if publication_identifiers:
            PublicationIdentifier.objects.bulk_create(
                PublicationIdentifier(publicatie=publication, **identifiers)
                for identifiers in publication_identifiers
            )

        # handle the publicatiestatus
        match publicatiestatus:
            case PublicationStatusOptions.concept:
                publication.draft()
            case PublicationStatusOptions.published:
                request: Request = self.context["request"]
                user_id, user_repr, remarks = extract_audit_parameters(request)
                publication.publish(
                    request,
                    user={"identifier": user_id, "display_name": user_repr},
                    remarks=remarks,
                )
                publication.apply_retention_policy(commit=False)
            case _:  # pragma: no cover
                raise ValueError(
                    f"Unexpected creation publicatiestatus: {publicatiestatus}"
                )

        publication.save()

        return publication


class TopicSerializer(serializers.ModelSerializer[Topic]):
    publicaties = serializers.SlugRelatedField(
        queryset=Publication.objects.all(),
        slug_field="uuid",
        help_text=_("The publication attached to this topic."),
        many=True,
        source="publication_set",
    )

    class Meta:  # pyright: ignore
        model = Topic
        fields = (
            "uuid",
            "afbeelding",
            "publicaties",
            "officiele_titel",
            "omschrijving",
            "publicatiestatus",
            "promoot",
            "registratiedatum",
            "laatst_gewijzigd_datum",
        )
