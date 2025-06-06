# Generated by Django 5.0.6 on 2025-02-04 12:38

from django.db import migrations, models

import data_map_backend.models


class Migration(migrations.Migration):

    dependencies = [
        ("data_map_backend", "0058_datacollection_notification_emails"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chat",
            name="chat_history",
            field=models.JSONField(blank=True, default=list, verbose_name="Chat History"),
        ),
        migrations.AlterField(
            model_name="datacollection",
            name="class_names",
            field=models.JSONField(
                blank=True,
                default=data_map_backend.models.class_field_default,
                help_text="Minimal list of classes shown in the UI, even if no items are present. More classes are deducted from items.",
                verbose_name="Class Names",
            ),
        ),
        migrations.AlterField(
            model_name="datasetschema",
            name="descriptive_text_fields",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="For Word2Vec, Cluster Titles and more",
                verbose_name="Descriptive Text Fields",
            ),
        ),
        migrations.AlterField(
            model_name="searchhistoryitem",
            name="parameters",
            field=models.JSONField(blank=True, default=dict, verbose_name="Parameters"),
        ),
        migrations.AlterField(
            model_name="searchhistoryitem",
            name="result_information",
            field=models.JSONField(blank=True, default=dict, verbose_name="Other Result Information"),
        ),
        migrations.AlterField(
            model_name="writingtask",
            name="additional_results",
            field=models.JSONField(blank=True, default=dict, verbose_name="Additional Results"),
        ),
    ]
