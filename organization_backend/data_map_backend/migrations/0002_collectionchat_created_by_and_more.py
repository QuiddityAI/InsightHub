# Generated by Django 5.0.3 on 2024-03-27 19:18

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='collectionchat',
            name='created_by',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Created By'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='collectionchat',
            name='search_settings',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Search Settings'),
        ),
        migrations.AlterField(
            model_name='collectionchat',
            name='class_name',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='Class'),
        ),
        migrations.AlterField(
            model_name='collectionchat',
            name='collection',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='data_map_backend.datacollection', verbose_name='Collection'),
        ),
    ]
