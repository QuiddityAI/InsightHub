# Generated by Django 5.0.6 on 2024-07-21 12:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("data_map_backend", "0012_alter_collectioncolumn_field_type_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="datasetfield",
            name="index_parameters",
            field=models.JSONField(default=dict, verbose_name="Index Parameters"),
        ),
    ]
