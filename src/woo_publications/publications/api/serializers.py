from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from woo_publications.contrib.documents_api.client import FilePart
from woo_publications.logging.service import extract_audit_parameters
from woo_publications.metadata.models import InformationCategory, Organisation

from ..constants import DocumentActionTypeOptions, PublicationStatusOptions
from ..models import Document, Publication, Topic


class EigenaarSerializer(serializers.Serializer):
    weergave_naam = serializers.CharField(
        source="display_name",
        read_only=True,
        help_text=_("The display name of the user, as recorded in the audit trails."),
    )
    identifier = serializers.CharField(
        read_only=True,
        help_text=_(
            "The system identifier that uniquely identifies the user performing the action."
        ),
    )


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
            "The document actions of this document, currently only one action will be used per document."
        ),
        required=False,
        many=True,
        min_length=1,  # pyright: ignore[reportCallIssue]
        max_length=1,  # pyright: ignore[reportCallIssue]
    )
    eigenaar = EigenaarSerializer(
        source="get_owner",
        label=_("owner"),
        help_text=_("The creator of the document, derived from the audit logs."),
        allow_null=True,
        read_only=True,
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

    def validate_publicatiestatus(
        self, value: PublicationStatusOptions
    ) -> PublicationStatusOptions:
        # new record
        if not self.instance:
            if value == PublicationStatusOptions.revoked:
                raise serializers.ValidationError(
                    _("You cannot create a {revoked} document.").format(
                        revoked=PublicationStatusOptions.revoked.label.lower()
                    )
                )

        return value


class DocumentUpdateSerializer(DocumentSerializer):
    publicatie = serializers.SlugRelatedField(
        slug_field="uuid",
        help_text=_("The unique identifier of the publication."),
        read_only=True,
    )
    documenthandelingen = DocumentActionSerializer(
        help_text=_(
            "The document actions of this document, currently only one action will be used per document."
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
        source="get_owner",
        label=_("owner"),
        help_text=_("The creator of the publication, derived from the audit logs."),
        allow_null=True,
        read_only=True,
    )
    informatie_categorieen = serializers.SlugRelatedField(
        queryset=InformationCategory.objects.all(),
        slug_field="uuid",
        help_text=_(
            "The information categories clarify the kind of information present in the publication."
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
            "Topics capture socially relevant information that spans multiple publications. "
            "They can remain relevant for tens of years and exceed the life span of a single publication."
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
                    "\n\n**Disclaimer**: when you revoke a publication, the attached published documents also get revoked."
                ).format(
                    revoked=PublicationStatusOptions.revoked.label.lower(),
                )
            },
            "bron_bewaartermijn": {
                "help_text": _(
                    "The source of the retention policy (example: Selectielijst gemeenten 2020)."
                    "\n\n**Note** on create or when updating the information categories, manually provided values are ignored "
                    "and overwritten by the automatically derived parameters from the related information categories."
                )
            },
            "selectiecategorie": {
                "help_text": _(
                    "The category as specified in the provided retention policy source (example: 20.1.2)."
                    "\n\n**Note** on create or when updating the information categories, manually provided values are ignored "
                    "and overwritten by the automatically derived parameters from the related information categories."
                )
            },
            "archiefnominatie": {
                "help_text": _(
                    "Determines if the archived data will be retained or destroyed."
                    "\n\n**Note** on create or when updating the information categories, manually provided values are ignored "
                    "and overwritten by the automatically derived parameters from the related information categories."
                )
            },
            "archiefactiedatum": {
                "help_text": _(
                    "Date when the publication will be archived or destroyed."
                    "\n\n**Note** on create or when updating the information categories, manually provided values are ignored "
                    "and overwritten by the automatically derived parameters from the related information categories."
                )
            },
            "toelichting_bewaartermijn": {
                "help_text": _(
                    "**Note** on create or when updating the information categories, manually provided values are ignored "
                    "and overwritten by the automatically derived parameters from the related information categories."
                )
            },
        }

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
        # new record
        else:
            if value == PublicationStatusOptions.revoked:
                raise serializers.ValidationError(
                    _("You cannot create a {revoked} publication.").format(
                        revoked=PublicationStatusOptions.revoked.label.lower()
                    )
                )

        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        assert instance.publicatiestatus != PublicationStatusOptions.revoked
        apply_retention = False

        if informatie_categorieen := validated_data.get("informatie_categorieen"):
            old_informatie_categorieen_set = {
                ic.uuid for ic in instance.informatie_categorieen.all()
            }
            new_informatie_categorieen_set = {ic.uuid for ic in informatie_categorieen}

            if old_informatie_categorieen_set != new_informatie_categorieen_set:
                apply_retention = True

        publication = super().update(instance, validated_data)

        if validated_data.get("publicatiestatus") == PublicationStatusOptions.revoked:
            user_id, user_repr, remarks = extract_audit_parameters(
                self.context["request"]
            )

            publication.revoke_own_published_documents(
                user={"identifier": user_id, "display_name": user_repr}, remarks=remarks
            )

        if apply_retention:
            publication.apply_retention_policy()

        return publication

    @transaction.atomic
    def create(self, validated_data):
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
