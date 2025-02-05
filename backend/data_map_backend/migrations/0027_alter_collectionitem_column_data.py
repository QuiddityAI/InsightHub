# Generated by Django 5.0.6 on 2024-10-06 15:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0026_collectioncolumn_determines_relevance_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collectionitem',
            name='column_data',
            field=models.JSONField(blank=True, default=dict, help_text='Extracted answers, notes, etc.', verbose_name='Column Data'),
        ),
    ]
