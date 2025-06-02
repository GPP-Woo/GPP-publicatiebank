import logging
from typing import TypedDict

from django.db import transaction
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.request import Request

from woo_publications.accounts.models import OrganisationMember
from woo_publications.api.drf_spectacular.headers import (
    AUDIT_USER_ID_PARAMETER,
    AUDIT_USER_REPRESENTATION_PARAMETER,
)
from woo_publications.contrib.documents_api.client import FilePart
from woo_publications.metadata.models import InformationCategory, Organisation

from ..constants import DocumentActionTypeOptions, PublicationStatusOptions
from ..models import Document, Publication, Topic
from .validators import PublicationStatusValidator

logger = logging.getLogger(__name__)


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


class DocumentActionSerializer(serializers.Serializer):
    soort_handeling = serializers.ChoiceField(
        choices=DocumentActionTypeOptions.choices,
        default=DocumentActionTypeOptions.declared,
    )
    identifier = serializers.URLField(read_only=True)
    at_time = serializers.DateTimeField(
        read_only=True,
    )
    was_assciated_with = serializers.UUIDField(
        help_text=_("The unique identifier of the organisation."),
        read_only=True,
    )


class DocumentStatusSerializer(serializers.Serializer):
    document_upload_voltooid = serializers.BooleanField(
        label=_("document upload completed"),
        help_text=_(
            "Indicates if all chunks of the file have been received and the document "
            "has been unlocked and made 'ready for use' in the upstream Documents API."
        ),
    )


class DocumentSerializer(serializers.ModelSerializer[Document]):
    publicatie = serializers.SlugRelatedField(
        queryset=Publication.objects.all(),
        slug_field="uuid",
        help_text=_("The unique identifier of the publication."),
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
    documenthandelingen = DocumentActionSerializer(
        help_text=_(
            "The document actions of this document, currently only one action will be "
            "used per document."
        ),
        required=False,
        many=True,
        min_length=1,  # pyright: ignore[reportCallIssue]
        max_length=1,  # pyright: ignore[reportCallIssue]
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
        model = Document
        fields = (
            "uuid",
            "identifier",
            "publicatie",
            "officiele_titel",
            "verkorte_titel",
            "omschrijving",
            "publicatiestatus",
            "creatiedatum",
            "bestandsformaat",
            "bestandsnaam",
            "bestandsomvang",
            "eigenaar",
            "registratiedatum",
            "laatst_gewijzigd_datum",
            "bestandsdelen",
            "documenthandelingen",
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

    def validate(self, attrs):
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

        return super().validate(attrs)

    @transaction.atomic
    def update(self, instance, validated_data):
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
                logger.debug(
                    "state_transition_skipped",
                    extra={
                        "source_status": current_publication_status,
                        "target_status": new_publication_status,
                        "model": instance._meta.model_name,
                        "pk": instance.pk,
                    },
                )

        return super().update(instance, validated_data)

    @transaction.atomic
    def create(self, validated_data):
        # on create, the status is always derived from the publication. Anything
        # submitted by the client is ignored.
        publication: Publication = validated_data["publicatie"]
        validated_data["publicatiestatus"] = publication.publicatiestatus

        validated_data["eigenaar"] = update_or_create_organisation_member(
            self.context["request"], validated_data.get("eigenaar")
        )
        return super().create(validated_data)


class DocumentUpdateSerializer(DocumentSerializer):
    publicatie = serializers.SlugRelatedField(
        slug_field="uuid",
        help_text=_("The unique identifier of the publication."),
        read_only=True,
    )
    documenthandelingen = DocumentActionSerializer(
        help_text=_(
            "The document actions of this document, currently only one action will be "
            "used per document."
        ),
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


class PublicationSerializer(serializers.ModelSerializer[Publication]):
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
    informatie_categorieen = serializers.SlugRelatedField(
        queryset=InformationCategory.objects.all(),
        slug_field="uuid",
        help_text=_(
            "The information categories clarify the kind of information present in "
            "the publication."
        ),
        many=True,
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

    class Meta:  # pyright: ignore
        model = Publication
        fields = (
            "uuid",
            "informatie_categorieen",
            "di_woo_informatie_categorieen",
            "onderwerpen",
            "publisher",
            "verantwoordelijke",
            "opsteller",
            "officiele_titel",
            "verkorte_titel",
            "omschrijving",
            "eigenaar",
            "publicatiestatus",
            "registratiedatum",
            "laatst_gewijzigd_datum",
            "bron_bewaartermijn",
            "selectiecategorie",
            "archiefnominatie",
            "archiefactiedatum",
            "toelichting_bewaartermijn",
        )
        extra_kwargs = {
            "uuid": {
                "read_only": True,
            },
            "registratiedatum": {
                "read_only": True,
            },
            "laatst_gewijzigd_datum": {
                "read_only": True,
            },
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

    @transaction.atomic
    def update(self, instance, validated_data):
        apply_retention = False

        # pop the target state from the validate data to avoid setting it directly,
        # instead apply the state transitions based on old -> new state
        current_publication_status: PublicationStatusOptions = instance.publicatiestatus
        new_publication_status: PublicationStatusOptions = validated_data.pop(
            "publicatiestatus",
            current_publication_status,
        )

        if "eigenaar" in validated_data:
            eigenaar = validated_data.pop("eigenaar")
            validated_data["eigenaar"] = OrganisationMember.objects.get_and_sync(
                identifier=eigenaar["identifier"], naam=eigenaar["naam"]
            )

        if informatie_categorieen := validated_data.get("informatie_categorieen"):
            old_informatie_categorieen_set = {
                ic.uuid for ic in instance.informatie_categorieen.all()
            }
            new_informatie_categorieen_set = {ic.uuid for ic in informatie_categorieen}

            if old_informatie_categorieen_set != new_informatie_categorieen_set:
                apply_retention = True

        match (current_publication_status, new_publication_status):
            case (PublicationStatusOptions.concept, PublicationStatusOptions.published):
                request: Request = self.context["request"]
                instance.publish(request)
            case (PublicationStatusOptions.published, PublicationStatusOptions.revoked):
                instance.revoke()
            case _:
                logger.debug(
                    "state_transition_skipped",
                    extra={
                        "source_status": current_publication_status,
                        "target_status": new_publication_status,
                        "model": instance._meta.model_name,
                        "pk": instance.pk,
                    },
                )

        publication = super().update(instance, validated_data)

        if apply_retention:
            publication.apply_retention_policy()

        return publication

    @transaction.atomic
    def create(self, validated_data):
        # pop the target state since we apply it through the transition methods instead
        # of setting it directly. The field default ensures that missing keys get a
        # default and the field disallows the empty string.
        publicatiestatus: PublicationStatusOptions = validated_data.pop(
            "publicatiestatus"
        )

        validated_data["eigenaar"] = update_or_create_organisation_member(
            self.context["request"], validated_data.get("eigenaar")
        )

        publication = super().create(validated_data)

        # handle the publicatiestatus
        match publicatiestatus:
            case PublicationStatusOptions.concept:
                publication.draft()
            case PublicationStatusOptions.published:
                request: Request = self.context["request"]
                publication.publish(request)
            case _:
                raise ValueError(
                    f"Unexpected creation publicatiestatus: {publicatiestatus}"
                )

        publication.apply_retention_policy()
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
