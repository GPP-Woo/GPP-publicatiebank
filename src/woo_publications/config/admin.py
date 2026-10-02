from functools import partial

from django import forms
from django.contrib import admin
from django.db import transaction
from django.http import HttpRequest

from solo.admin import SingletonModelAdmin

from woo_publications.contrib.catalogi_api.client import CatalogiAPIError, get_client
from woo_publications.publications.models import InzageProcedure

from .models import GlobalConfiguration
from .tasks import index_default_iot


@admin.register(GlobalConfiguration)
class GlobalConfigurationAdmin(SingletonModelAdmin):
    readonly_fields = ("catalogus_url", "default_iot_url")

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
    def _create_global_catalogi_api_objects(
        obj: GlobalConfiguration,
    ) -> str | None:
        service = obj.catalogi_api_service

        with get_client(service) as client:
            try:
                return client.create_catalogi(rsin=obj.organisation_rsin)
            except CatalogiAPIError:
                return

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

        # automatically create catalogi api objects needed for the Document API
        # documents
        if not obj.catalogus_url:
            if catalogi_url := self._create_global_catalogi_api_objects(obj):
                obj.catalogus_url = catalogi_url

        if not obj.default_iot_url:
            transaction.on_commit(partial(index_default_iot.delay))

        super().save_model(request, obj, form, change)
