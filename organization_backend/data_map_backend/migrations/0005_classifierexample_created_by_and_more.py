# Generated by Django 4.2.7 on 2023-11-23 18:06

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('data_map_backend', '0004_classifier_allow_multi_class_classifier_class_names_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='classifierexample',
            name='created_by',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='User'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='classifierexample',
            name='is_public',
            field=models.BooleanField(default=False, verbose_name='Is public'),
        ),
    ]
