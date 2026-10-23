from functools import partial

from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from solo.admin import SingletonModelAdmin

from woo_publications.publications.models import InzageProcedure

from .models import CatalogiSetupError, GlobalConfiguration


@admin.register(GlobalConfiguration)
class GlobalConfigurationAdmin(SingletonModelAdmin):
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(
            db_field=db_field, request=request, **kwargs
        )

        match db_field.name:
            case "gpp_app_publication_url_template":
                assert field is not None
                field.widget.attrs.setdefault(
                    "placeholder", "https://gpp-app.example.com/publicaties/<UUID>"
                )
            case "gpp_burgerportaal_publication_url_template":
                assert field is not None
                field.widget.attrs.setdefault(
                    "placeholder",
                    "https://gpp-burgerportaal.example.com/publicaties/<UUID>",
                )

        return field

    @staticmethod
    def _back_fill_url_reactieformulier():
        objects = InzageProcedure.objects.filter(url_reactieformulier="")

        for inzage_procedure in objects:
            inzage_procedure.set_url_reactieformulier(
                beschikbaar_rechtsmiddel=inzage_procedure.beschikbaar_rechtsmiddel,
                url_reactieformulier=inzage_procedure.url_reactieformulier,
            )

        InzageProcedure.objects.bulk_update(objects, fields=["url_reactieformulier"])

    @staticmethod
    def _create_global_catalogi_api_objects(request: HttpRequest) -> None:
        try:
            GlobalConfiguration.setup_catalogi_api()
        except CatalogiSetupError as err:
            messages.add_message(request, messages.ERROR, str(err))
            return

        messages.add_message(
            request,
            messages.INFO,
            _(
                "Catalogi API has been set up successfully. The Information Categories "
                "and Documents will now be processed in the background."
            ),
        )

    def save_model(
        self,
        request: HttpRequest,
        obj: GlobalConfiguration,
        form: forms.Form,
        change: bool,
    ):
        # since these fields are required we just need to check if the
        # initial was originally empty. This function will only trigger
        # once and then never again.
        if (
            not form.initial["perspective_reaction_form_url"]
            and not form.initial["objection_reaction_form_url"]
        ):
            transaction.on_commit(partial(self._back_fill_url_reactieformulier))

        if (
            not form.cleaned_data["catalogus_url"]
            or not form.cleaned_data["default_iot_url"]
        ):
            transaction.on_commit(
                partial(self._create_global_catalogi_api_objects, request=request)
            )

        super().save_model(request, obj, form, change)
