# Generated by Django 4.2.4 on 2023-08-28 10:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0005_historicalobjectfield_index_parameters_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalobjectschema',
            name='primary_key',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='data_map_backend.objectfield', verbose_name='Primary Key'),
        ),
        migrations.AddField(
            model_name='objectschema',
            name='primary_key',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='data_map_backend.objectfield', verbose_name='Primary Key'),
        ),
        migrations.AlterField(
            model_name='objectschema',
            name='thumbnail_image',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='data_map_backend.objectfield', verbose_name='Thumbnail Image'),
        ),
    ]
