from functools import partial

from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from solo.admin import SingletonModelAdmin
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from woo_publications.contrib.catalogi_api.client import CatalogiAPIError, get_client
from woo_publications.publications.models import InzageProcedure

from .models import GlobalConfiguration
from .tasks import sync_information_categories_and_documents_with_catalog_api


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
    @transaction.atomic()
    def _create_global_catalogi_api_objects(request: HttpRequest) -> None:
        config = GlobalConfiguration.objects.select_for_update().get(
            pk=GlobalConfiguration.singleton_instance_id
        )
        service = config.catalogi_api_service

        if service.connection_check != 200:
            messages.add_message(
                request,
                messages.ERROR,
                _(
                    "The Catalogi API service is not available. "
                    "Because of this the Catalogi and default Informationobjecttypes "
                    "couldn't be created. Check if you configured the Service "
                    "correctly and make sure that it is running correctly."
                ),
            )
            return

        with get_client(service) as client:
            if (catalogi := config.catalogus_url) == "":
                try:
                    catalogi = config.catalogus_url = client.create_catalogi(
                        rsin=config.organisation_rsin
                    )
                except CatalogiAPIError:
                    messages.add_message(
                        request,
                        messages.ERROR,
                        _("Something went wrong while trying to create the Catalogi."),
                    )
                    return

            try:
                iot = client.create_iot(
                    description=(
                        "informatieobjecttypen of publications with no information "
                        "category objects."
                    ),
                    catalogus=catalogi,
                    confidentiality_indication=VertrouwelijkheidsAanduidingen.vertrouwelijk,
                )
                config.default_iot_url = iot.url
            except CatalogiAPIError:
                messages.add_message(
                    request,
                    messages.ERROR,
                    _(
                        "Something went wrong while trying to create the default "
                        "Informationobjecttypes."
                    ),
                )
                config.save(update_fields=("catalogus_url",))
                return

        messages.add_message(
            request,
            messages.INFO,
            _(
                "Catalogi API has been set up successfully. The Information Categories "
                "and Documents will now be processed in the background."
            ),
        )
        transaction.on_commit(
            partial(
                sync_information_categories_and_documents_with_catalog_api.delay,
                confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar,
            )
        )
        config.save(
            update_fields=(
                "catalogus_url",
                "default_iot_url",
            )
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

        if not obj.catalogus_url or not obj.default_iot_url:
            transaction.on_commit(
                partial(self._create_global_catalogi_api_objects, request=request)
            )

        super().save_model(request, obj, form, change)
