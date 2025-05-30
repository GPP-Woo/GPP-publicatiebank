# Generated by Django 4.2.16 on 2024-10-30 10:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("metadata", "0005_organisation"),
        (
            "publications",
            "0004_document_uuid_alter_document_identifier",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="publication",
            name="informatie_categorieen",
            field=models.ManyToManyField(
                help_text="The information categories clarify the kind of information present in the publication.",
                to="metadata.informationcategory",
                verbose_name="information categories",
            ),
        ),
    ]
