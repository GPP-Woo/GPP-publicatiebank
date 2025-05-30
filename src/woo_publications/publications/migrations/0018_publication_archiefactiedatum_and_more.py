# Generated by Django 4.2.19 on 2025-04-10 09:03

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("publications", "0017_alter_topic_publicatiestatus"),
    ]

    operations = [
        migrations.AddField(
            model_name="publication",
            name="archiefactiedatum",
            field=models.DateField(
                blank=True,
                help_text="Date when the publication will be archived or destroyed.",
                null=True,
                verbose_name="archive action date",
            ),
        ),
        migrations.AddField(
            model_name="publication",
            name="archiefnominatie",
            field=models.CharField(
                blank=True,
                choices=[("blijvend_bewaren", "Retain"), ("vernietigen", "Destroy")],
                help_text="Determines if the archived data will be retained or destroyed.",
                max_length=50,
                verbose_name="archive action",
            ),
        ),
        migrations.AddField(
            model_name="publication",
            name="bron_bewaartermijn",
            field=models.CharField(
                blank=True,
                help_text="The source of the retention policy (example: Selectielijst gemeenten 2020).",
                max_length=255,
                verbose_name="retention policy source",
            ),
        ),
        migrations.AddField(
            model_name="publication",
            name="selectiecategorie",
            field=models.CharField(
                blank=True,
                help_text="The category as specified in the provided retention policy source (example: 20.1.2).",
                max_length=255,
                verbose_name="selection category",
            ),
        ),
        migrations.AddField(
            model_name="publication",
            name="toelichting_bewaartermijn",
            field=models.TextField(
                blank=True, verbose_name="retention policy explanation"
            ),
        ),
    ]
