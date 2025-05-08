from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from woo_publications.accounts.models import OrganisationMember


class ChangeOwnerForm(forms.Form):
    eigenaar = forms.ModelChoiceField(
        label=_("Owner"),
        queryset=OrganisationMember.objects.all(),
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
                raise ValidationError(
                    _("You need to provide a valid `owner` or `identifier` and `name`.")
                )
            case (True, False, False):
                pass
            case (False, True, False):
                raise ValidationError({"naam": _("This field is required.")})
            case (False, False, True):
                raise ValidationError({"identifier": _("This field is required.")})

        return cleaned_data
