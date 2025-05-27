from typing import TypedDict

from django.db import transaction
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from django_fsm import TransitionNotAllowed
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

from ..constants import DocumentActionTypeOptions, PublicationStatusOptions
from ..models import Document, LinkedPublicationError, Publication, Topic


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


class DocumentSerializer(serializers.ModelSerializer):
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
                "help_text": _(
                    "\n**Disclaimer**: you can't create a {revoked} document."
                ).format(revoked=PublicationStatusOptions.revoked.label.lower())
            },
        }

    def _change_publicatie_status(
        self,
        document: Document,
        publicatiestatus=PublicationStatusOptions,
        publicatie_id: int | None = None,
    ):
        mappings = [
            {
                "transition": document.concept,
                "status": PublicationStatusOptions.concept,
                "message": _("You cannot set the status to {concept}.").format(
                    concept=PublicationStatusOptions.concept.label.lower()
                ),
            },
            {
                "transition": document.published,
                "status": PublicationStatusOptions.published,
                "message": _("You cannot set the status to {published}.").format(
                    published=PublicationStatusOptions.published.label.lower()
                ),
            },
            {
                "transition": document.revoked,
                "status": PublicationStatusOptions.revoked,
                "message": _("You cannot set the status to {revoked}.").format(
                    revoked=PublicationStatusOptions.revoked.label.lower()
                ),
            },
        ]

        for mapping in mappings:
            if mapping["status"] == publicatiestatus:
                try:
                    return mapping["transition"](publicatie_id)
                except TransitionNotAllowed as err:
                    raise serializers.ValidationError(
                        {"publicatiestatus": mapping["message"]}
                    ) from err
                except LinkedPublicationError as err:
                    raise serializers.ValidationError(
                        {"publicatiestatus": err}
                    ) from err

    def validate_publicatiestatus(
        self, value: PublicationStatusOptions
    ) -> PublicationStatusOptions:
        if self.instance:
            assert isinstance(self.instance, Document)

            if self.instance.publicatiestatus == PublicationStatusOptions.revoked:
                raise serializers.ValidationError(
                    _("You cannot modify a {revoked} document.").format(
                        revoked=PublicationStatusOptions.revoked.label.lower()
                    )
                )

        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        if publicatiestatus := validated_data.get("publicatiestatus"):
            publicatie = validated_data.get("publicatie", instance.publicatie)
            self._change_publicatie_status(
                document=instance,
                publicatiestatus=publicatiestatus,
                publicatie_id=publicatie.pk,
            )

        if "eigenaar" in validated_data:
            eigenaar = validated_data.pop("eigenaar")
            validated_data["eigenaar"] = OrganisationMember.objects.get_and_sync(
                identifier=eigenaar["identifier"], naam=eigenaar["naam"]
            )

        return super().update(instance, validated_data)

    @transaction.atomic
    def create(self, validated_data):
        publicatiestatus = validated_data["publicatie"].publicatiestatus

        self._change_publicatie_status(
            document=self.Meta.model(),
            publicatiestatus=publicatiestatus,
            publicatie_id=validated_data["publicatie"].pk,
        )

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
            )
        ]
        extra_kwargs = {
            "officiele_titel": {
                "required": False,
            }
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

    def _change_publicatie_status(
        self,
        request: Request,
        publication: Publication,
        publicatiestatus: PublicationStatusOptions,
    ):
        user_id, user_repr, remarks = extract_audit_parameters(request)

        mappings = [
            {
                "transition": publication.concept,
                "status": PublicationStatusOptions.concept,
                "message": _("You cannot set the status to {concept}.").format(
                    concept=PublicationStatusOptions.concept.label.lower()
                ),
            },
            {
                "transition": publication.published,
                "status": PublicationStatusOptions.published,
                "message": _("You cannot set the status to {published}.").format(
                    published=PublicationStatusOptions.published.label.lower()
                ),
            },
            {
                "transition": publication.revoked,
                "status": PublicationStatusOptions.revoked,
                "message": _("You cannot set the status to {revoked}.").format(
                    revoked=PublicationStatusOptions.revoked.label.lower()
                ),
            },
        ]

        for mapping in mappings:
            if mapping["status"] == publicatiestatus:
                try:
                    return mapping["transition"](
                        request=request,
                        user={
                            "identifier": user_id,
                            "display_name": user_repr,
                        },
                        remarks=remarks,
                    )
                except TransitionNotAllowed as err:
                    raise serializers.ValidationError(
                        {"publicatiestatus": mapping["message"]}
                    ) from err

    def validate_publicatiestatus(
        self, value: PublicationStatusOptions
    ) -> PublicationStatusOptions:
        # existing record
        if self.instance:
            assert isinstance(self.instance, Publication)

            if self.instance.publicatiestatus == PublicationStatusOptions.revoked:
                raise serializers.ValidationError(
                    _("You cannot modify a {revoked} publication.").format(
                        revoked=PublicationStatusOptions.revoked.label.lower()
                    )
                )

        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        assert instance.publicatiestatus != PublicationStatusOptions.revoked
        apply_retention = False

        if publicatiestatus := validated_data.get("publicatiestatus"):
            self._change_publicatie_status(
                request=self.context["request"],
                publication=instance,
                publicatiestatus=publicatiestatus,
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

        publication = super().update(instance, validated_data)

        if apply_retention:
            publication.apply_retention_policy()

        return publication

    @transaction.atomic
    def create(self, validated_data):
        publicatiestatus = validated_data.get(
            "publicatiestatus", PublicationStatusOptions.published
        )

        validated_data["eigenaar"] = update_or_create_organisation_member(
            self.context["request"], validated_data.get("eigenaar")
        )

        self._change_publicatie_status(
            request=self.context["request"],
            publication=self.Meta.model(),
            publicatiestatus=publicatiestatus,
        )

        publication = super().create(validated_data)
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
