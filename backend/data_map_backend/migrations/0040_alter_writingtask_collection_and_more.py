# Generated by Django 5.0.6 on 2024-12-06 12:49

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("data_map_backend", "0039_update_writing_task_model_to_new_models"),
    ]

    operations = [
        migrations.AlterField(
            model_name="writingtask",
            name="collection",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="data_map_backend.datacollection",
                verbose_name="Collection",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="writingtask",
            name="previous_versions",
            field=models.JSONField(blank=True, default=list, verbose_name="Previous Versions"),
        ),
        migrations.AlterField(
            model_name="writingtask",
            name="selected_item_ids",
            field=models.JSONField(blank=True, default=list, verbose_name="Selected Item IDs"),
        ),
        migrations.AlterField(
            model_name="writingtask",
            name="source_fields",
            field=models.JSONField(blank=True, default=list, verbose_name="Source Fields"),
        ),
    ]
