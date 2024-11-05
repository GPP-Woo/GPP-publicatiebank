# Generated by Django 4.2.16 on 2024-11-05 15:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("publications", "0006_merge_20241101_1532"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="laatst_geweizigd_datum",
            field=models.DateTimeField(
                auto_now=True,
                help_text="System timestamp reflecting when the document was last modified in the database.",
                verbose_name="last modified",
            ),
        ),
        migrations.AddField(
            model_name="publication",
            name="laatst_geweizigd_datum",
            field=models.DateTimeField(
                auto_now=True,
                help_text="System timestamp reflecting when the publication was last modified in the database.",
                verbose_name="last modified",
            ),
        ),
        migrations.AlterField(
            model_name="document",
            name="registratiedatum",
            field=models.DateTimeField(
                auto_now_add=True,
                help_text="System timestamp reflecting when the document was registered in the database. Not to be confused with the creation date of the document, which is usually *before* the registration date.",
                verbose_name="created on",
            ),
        ),
    ]
