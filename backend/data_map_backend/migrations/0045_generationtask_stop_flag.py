# Generated by Django 5.0.6 on 2025-01-02 15:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0044_generationtask_batch_size_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='generationtask',
            name='stop_flag',
            field=models.BooleanField(default=False, verbose_name='Stop Flag'),
        ),
    ]
