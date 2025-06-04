from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import GlobalConfiguration


@admin.register(GlobalConfiguration)
class GlobalConfigurationAdmin(SingletonModelAdmin):
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(
            db_field=db_field, request=request, **kwargs
        )

        if db_field.name == "gpp_app_publication_url_template":
            field.widget.attrs.setdefault(
                "placeholder", "https://gpp-app.example.com/publicaties/<UUID>"
            )

        return field
