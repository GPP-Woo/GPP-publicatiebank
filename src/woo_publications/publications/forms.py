from django import forms
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from django_fsm import TransitionNotAllowed

from woo_publications.accounts.models import OrganisationMember, User
from woo_publications.publications.constants import PublicationStatusOptions
from woo_publications.publications.models import (
    Document,
    LinkedPublicationError,
    Publication,
)


class ChangeOwnerForm(forms.Form):
    eigenaar = forms.ModelChoiceField(
        label=_("Owner"),
        queryset=OrganisationMember.objects.order_by("naam"),
        required=False,
    )
    identifier = forms.CharField(
        label=_("Identifier"),
        help_text=_("The (primary) unique identifier."),
        max_length=255,
        required=False,
    )
    naam = forms.CharField(
        label=_("Name"),
        max_length=255,
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        assert isinstance(cleaned_data, dict)

        has_eigenaar = bool(cleaned_data.get("eigenaar"))
        has_identifier = bool(cleaned_data.get("identifier"))
        has_naam = bool(cleaned_data.get("naam"))

        match (has_eigenaar, has_identifier, has_naam):
            case (False, False, False):
                self.add_error(
                    None,
                    error=_(
                        "You need to provide a valid 'owner' or "
                        "'identifier' and 'name'."
                    ),
                )
            case (True, False, False):
                pass
            case (False, True, False):
                self.add_error("naam", error=_("This field is required."))
            case (False, False, True):
                self.add_error("identifier", error=_("This field is required."))

        return cleaned_data


class PublicationForm(forms.ModelForm):
    publicatiestatus = forms.ChoiceField(
        label=_("Status"),
        choices=PublicationStatusOptions,
        required=True,
    )
    request: HttpRequest

    class Meta:
        model = Publication
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        assert isinstance(self.request.user, User)
        assert isinstance(self.instance, Publication)
        assert isinstance(cleaned_data, dict)

        user = self.request.user
        publication = self.instance

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
            if mapping["status"] == cleaned_data["publicatiestatus"]:
                try:
                    mapping["transition"](
                        request=self.request,
                        user={
                            "identifier": user.pk,
                            "display_name": user.get_full_name() or user.username,
                        },
                    )
                except TransitionNotAllowed:
                    self.add_error(field="publicatiestatus", error=mapping["message"])

        return cleaned_data


class DocumentForm(forms.ModelForm):
    publicatiestatus = forms.ChoiceField(
        label=_("Status"),
        choices=PublicationStatusOptions,
        required=True,
    )

    class Meta:
        model = Document
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        publicatiestatus_generic_error = False
        assert isinstance(self.instance, Document)
        assert isinstance(cleaned_data, dict)

        document = self.instance
        publicatie = cleaned_data["publicatie"]

        if not document.pk:
            publicatiestatus_generic_error = True
            cleaned_data["publicatiestatus"] = publicatie.publicatiestatus

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
            if mapping["status"] == cleaned_data["publicatiestatus"]:
                try:
                    mapping["transition"](publicatie_id=cleaned_data["publicatie"].pk)
                except TransitionNotAllowed:
                    self.add_error(
                        field="publicatiestatus"
                        if not publicatiestatus_generic_error
                        else None,
                        error=mapping["message"],
                    )
                except LinkedPublicationError as err:
                    self.add_error(
                        field="publicatiestatus"
                        if not publicatiestatus_generic_error
                        else None,
                        error=err.message,
                    )

        return cleaned_data
