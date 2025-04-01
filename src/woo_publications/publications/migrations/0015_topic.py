# Generated by Django 4.2.19 on 2025-03-25 16:32

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("publications", "0014_mark_existing_uploads_complete"),
    ]

    operations = [
        migrations.CreateModel(
            name="Topic",
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
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                        verbose_name="UUID",
                    ),
                ),
                (
                    "officiele_titel",
                    models.CharField(max_length=255, verbose_name="official title"),
                ),
                (
                    "omschrijving",
                    models.TextField(blank=True, verbose_name="description"),
                ),
                (
                    "publicatiestatus",
                    models.CharField(
                        choices=[
                            ("gepubliceerd", "Published"),
                            ("ingetrokken", "Revoked"),
                        ],
                        default="gepubliceerd",
                        max_length=12,
                        verbose_name="status",
                    ),
                ),
                (
                    "promoot",
                    models.BooleanField(
                        default=False, help_text="TODO", verbose_name="promote"
                    ),
                ),
                (
                    "registratiedatum",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="System timestamp reflecting when the topic was registered in the database.",
                        verbose_name="created on",
                    ),
                ),
                (
                    "laatst_gewijzigd_datum",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="System timestamp reflecting when the topic was last modified in the database.",
                        verbose_name="last modified",
                    ),
                ),
            ],
            options={
                "verbose_name": "topic",
                "verbose_name_plural": "topics",
            },
        ),
    ]
