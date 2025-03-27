# Generated by Django 4.2.19 on 2025-03-27 10:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("publications", "0015_topic"),
    ]

    operations = [
        migrations.AddField(
            model_name="publication",
            name="onderwerpen",
            field=models.ManyToManyField(
                blank=True,
                help_text="The topics clarify the kind of information present in the publication.",
                to="publications.topic",
                verbose_name="topics",
            ),
        ),
    ]
