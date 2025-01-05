# Generated by Django 5.0.6 on 2025-01-05 15:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0046_datasetschema_all_parents_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='datacollection',
            name='search_tasks',
            field=models.JSONField(blank=True, default=list, help_text='List of executed search tasks', verbose_name='Search Tasks'),
        ),
        migrations.AlterField(
            model_name='datacollection',
            name='last_search_task',
            field=models.JSONField(blank=True, default=dict, help_text='if search mode is still active, this is the current search task', verbose_name='Last Search Task'),
        ),
    ]
