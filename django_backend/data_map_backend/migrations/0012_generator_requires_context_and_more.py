# Generated by Django 4.2.4 on 2023-08-31 17:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0011_historicalobjectschema_map_rendering_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='generator',
            name='requires_context',
            field=models.BooleanField(default=False, verbose_name='Requires context'),
        ),
        migrations.AddField(
            model_name='historicalgenerator',
            name='requires_context',
            field=models.BooleanField(default=False, verbose_name='Requires context'),
        ),
    ]
