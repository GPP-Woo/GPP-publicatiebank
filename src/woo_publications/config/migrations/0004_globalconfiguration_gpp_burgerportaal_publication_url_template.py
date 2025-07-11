# Generated by Django 5.2.3 on 2025-06-17 13:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("config", "0003_globalconfiguration_gpp_app_publication_url_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="globalconfiguration",
            name="gpp_burgerportaal_publication_url_template",
            field=models.URLField(
                blank=True,
                default="",
                help_text="URL pattern to a publication in the GPP burgerportaal. The special token <UUID> will be replaced with the system identifier of each publication.",
                max_length=500,
                verbose_name="GPP-burgerportaal publication URL template",
            ),
        ),
    ]
