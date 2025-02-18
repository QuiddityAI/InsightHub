# Generated by Django 5.0.6 on 2024-10-05 08:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("data_map_backend", "0023_datacollection_search_sources_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="datacollection",
            name="last_search_task",
            field=models.JSONField(blank=True, default=dict, verbose_name="Last Search Task"),
        ),
        migrations.AddField(
            model_name="historicaldatacollection",
            name="last_search_task",
            field=models.JSONField(blank=True, default=dict, verbose_name="Last Search Task"),
        ),
    ]
