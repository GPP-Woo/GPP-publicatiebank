# Generated by Django 4.2.16 on 2024-11-06 13:10

import django.db.models.deletion
from django.db import migrations, models

import woo_publications.config.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("zgw_consumers", "0022_set_default_service_slug"),
    ]

    operations = [
        migrations.CreateModel(
            name="GlobalConfiguration",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "organisation_rsin",
                    models.CharField(
                        help_text="The RSIN of the municipality that owns the documents in the Documents API.",
                        max_length=9,
                        validators=[woo_publications.config.validators.validate_rsin],
                        verbose_name="organisation RSIN",
                    ),
                ),
                (
                    "documents_api_service",
                    models.ForeignKey(
                        help_text="The service to use for new document uploads - the metadata and binary content will be sent to this API.",
                        limit_choices_to={"api_type": "drc"},
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="zgw_consumers.service",
                        verbose_name="Documents API service",
                    ),
                ),
            ],
            options={
                "verbose_name": "global configuration",
            },
        ),
    ]