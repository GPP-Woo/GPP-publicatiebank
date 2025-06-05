from django import forms
from django.utils.translation import gettext_lazy as _

from woo_publications.accounts.models import OrganisationMember
from woo_publications.typing import is_authenticated_request

from .constants import PublicationStatusOptions


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


class PublicationStatusForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        self.initial_publicatiestatus = self.instance.publicatiestatus or ""

        if self.instance and self.fields.get("publicatiestatus"):
            allowed_values: list[str] = [
                status.target.value
                for status in self.instance.get_available_publicatiestatus_transitions()
            ]

            if selected_publicatiestatus := self.instance.publicatiestatus:
                allowed_values.append(selected_publicatiestatus)

            self.fields["publicatiestatus"].choices = [  # pyright: ignore[reportAttributeAccessIssue]
                choice
                for choice in PublicationStatusOptions.choices
                if choice[0] in allowed_values
            ]


class PublicationAdminForm(PublicationStatusForm):
    def save(self, commit=True):
        assert is_authenticated_request(self.request)
        publicatie_status = self.cleaned_data["publicatiestatus"]

        publication = super().save(commit=commit)
        # cannot force the commit as True because of the AttributeError:
        # 'PublicationForm' object has no attribute 'save_m2m'.
        # So we manually save it after running the super
        publication.save()

        self.instance.publicatiestatus = self.initial_publicatiestatus

        if publicatie_status == PublicationStatusOptions.published:
            publication.publish(self.request, user=self.request.user)

        elif self.initial_publicatiestatus != publicatie_status:
            match publicatie_status:
                case PublicationStatusOptions.concept:
                    publication.draft()
                case PublicationStatusOptions.revoked:
                    publication.revoke(user=self.request.user)

        publication.refresh_from_db()

        return publication


class DocumentAdminForm(PublicationStatusForm):
    def save(self, commit=True):
        publicatie_status = self.instance.publicatie.publicatiestatus
        if (
            self.cleaned_data.get("publicatiestatus")
            == PublicationStatusOptions.revoked
        ):
            publicatie_status = PublicationStatusOptions.revoked

        self.instance.publicatiestatus = publicatie_status

        document = super().save(commit=commit)
        # cannot force the commit as True because of the AttributeError:
        # 'DocumentForm' object has no attribute 'save_m2m'.
        # So we manually save it after running the super
        document.save()

        self.instance.publicatiestatus = self.initial_publicatiestatus

        if publicatie_status == PublicationStatusOptions.published:
            document.publish(self.request)

        elif self.initial_publicatiestatus != publicatie_status:
            match publicatie_status:
                case PublicationStatusOptions.concept:
                    document.draft()
                case PublicationStatusOptions.revoked:
                    document.revoke()

        document.refresh_from_db()

        return document
