from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import GlobalConfiguration


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
