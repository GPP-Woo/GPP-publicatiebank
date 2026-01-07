from collections.abc import Sequence
from functools import partial
from typing import Literal

from django.db import transaction
from django.utils.translation import gettext_lazy as _

import structlog
from django_fsm import FSMField
from drf_polymorphic.serializers import PolymorphicSerializer
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.relations import ManyRelatedField, SlugRelatedField
from rest_framework.request import Request

from woo_publications.accounts.models import OrganisationMember, OrganisationUnit
from woo_publications.logging.api_tools import extract_audit_parameters
from woo_publications.metadata.models import InformationCategory, Organisation

from ...constants import PublicationStatusOptions
from ...models import (
    Publication,
    PublicationIdentifier,
    Topic,
)
from ...tasks import index_document, index_publication
from ...typing import Kenmerk
from ..utils import _get_fsm_help_text
from ..validators import PublicationStatusValidator, validate_duplicated_kenmerken
from .owner import (
    EigenaarGroepSerializer,
    EigenaarSerializer,
    update_or_create_organisation_member,
    update_or_create_organisation_unit,
)

logger = structlog.stdlib.get_logger(__name__)


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
            "URL to the UI of the external application where the publication is "
            "publicly visible. Requires the global configuration parameter to be "
            "set, otherwise an empty string is returned."
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
        allow_null=True,
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
    eigenaar_groep = EigenaarGroepSerializer(
        label=_("owner (group)"),
        help_text=_(
            "Optional organisation unit that also owns the publication, in addition to "
            "the `eigenaar` property."
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
            "eigenaar_groep",
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
        }

    def get_fields(self):
        fields = super().get_fields()

        assert fields["publicatiestatus"].help_text
        fsm_field = Publication._meta.get_field("publicatiestatus")
        assert isinstance(fsm_field, FSMField)
        fields["publicatiestatus"].help_text += _get_fsm_help_text(fsm_field)
        return fields

    def validate_kenmerken(self, value: Sequence[Kenmerk]) -> Sequence[Kenmerk]:
        validate_duplicated_kenmerken(value)
        return value

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

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            # for reach operations, we can guarantee that all the fields will be present
            # in the response body (that does *not* mean they have a non-empty value!)
            field.required = True

        # publisher field
        publisher = fields["publisher"]
        assert isinstance(publisher, SlugRelatedField)
        publisher.help_text += _(
            " The publisher can be `null` if the publication is a concept."
        )

        # owner (explicitly set or via audit trails)
        fields["eigenaar"].allow_null = False

        return fields


class PublicationWriteBaseSerializer(PublicationSerializer):
    def get_fields(self):
        fields = super().get_fields()

        # Add notice about submitted values being overwritten on create
        for _field_name in (
            "bron_bewaartermijn",
            "selectiecategorie",
            "archiefnominatie",
            "archiefactiedatum",
            "toelichting_bewaartermijn",
        ):
            field = fields[_field_name]
            extra_help = _(
                "\n\n**Note** on create or when updating the information "
                "categories, manually provided values are ignored and overwritten "
                "by the automatically derived parameters from the related "
                "information categories."
            )
            if not field.help_text:
                extra_help = extra_help.strip()
                field.help_text = ""  # normalize to str
            field.help_text += extra_help

        return fields

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


class ConceptPublicationWriteSerializer(PublicationWriteBaseSerializer):
    def get_fields(self):
        fields = super().get_fields()

        information_categories_field = fields["informatie_categorieen"]
        assert isinstance(information_categories_field, ManyRelatedField)
        information_categories_field.required = False
        information_categories_field.allow_empty = True

        # publisher field
        publisher = fields["publisher"]
        assert isinstance(publisher, SlugRelatedField)
        publisher.required = False

        return fields


class PublishedOrRevokedPublicationWriteSerializer(PublicationWriteBaseSerializer):
    def get_fields(self):
        fields = super().get_fields()

        # publisher field
        publisher = fields["publisher"]
        assert isinstance(publisher, SlugRelatedField)
        publisher.allow_null = False

        return fields


class PublicationWriteSerializer(
    PolymorphicSerializer, serializers.ModelSerializer[Publication]
):
    """
    Encapsulate the create/update validation logic and behaviour.

    The publication serializer is split in read/write parts so that the output can be
    properly documented in the API schema. Writes for concept publications are much
    more relaxed that published publications.

    The write serializer in turn is a polymorphic serializer, covering the validation
    behaviour for concept/published publication states.

    .. todo:: test validation behaviour of an incomplete concept publication being
    changed to published.
    """

    discriminator_field = "publicatiestatus"
    serializer_mapping = {
        PublicationStatusOptions.concept: ConceptPublicationWriteSerializer,
        PublicationStatusOptions.published: PublishedOrRevokedPublicationWriteSerializer,  # noqa: E501
        PublicationStatusOptions.revoked: PublishedOrRevokedPublicationWriteSerializer,
    }

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = Publication
        fields = ("publicatiestatus",)
        extra_kwargs = {
            "publicatiestatus": PublicationSerializer.Meta.extra_kwargs[
                "publicatiestatus"
            ],
        }

    def to_internal_value(self, data):
        # ensure that for (partial) updates, we add the existing instance discriminator
        # value to the data instead of falling back to the default
        # TODO: patch up in drf-polymorphic
        if self.instance is not None and self.discriminator_field not in data:
            data[self.discriminator_field] = self.discriminator.get_attribute(
                self.instance
            )
        return super().to_internal_value(data)

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
        initial_publisher = instance.publisher

        if "eigenaar" in validated_data:
            if eigenaar := validated_data.pop("eigenaar"):
                validated_data["eigenaar"] = OrganisationMember.objects.get_and_sync(
                    identifier=eigenaar["identifier"], naam=eigenaar["naam"]
                )

        if (
            "eigenaar_groep" in validated_data
            and (org_unit := validated_data.pop("eigenaar_groep")) is not None
        ):
            validated_data["eigenaar_groep"] = OrganisationUnit.objects.get_and_sync(
                identifier=org_unit["identifier"], naam=org_unit["naam"]
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

        if (
            "publisher" in validated_data
            and initial_publisher != validated_data["publisher"]
        ):
            instance.update_documents_rsin()

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

        if (org_unit_details := validated_data.get("eigenaar_groep")) is not None:
            validated_data["eigenaar_groep"] = update_or_create_organisation_unit(
                org_unit_details
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
