# Generated by Django 4.2.4 on 2023-08-30 09:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0008_remove_historicalobjectfield_is_required_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalobjectfield',
            name='generating_condition',
            field=models.TextField(blank=True, null=True, verbose_name='Generating Condition'),
        ),
        migrations.AlterField(
            model_name='historicalobjectfield',
            name='generator_parameters',
            field=models.TextField(blank=True, null=True, verbose_name='Generator Parameters'),
        ),
        migrations.AlterField(
            model_name='objectfield',
            name='generating_condition',
            field=models.TextField(blank=True, null=True, verbose_name='Generating Condition'),
        ),
        migrations.AlterField(
            model_name='objectfield',
            name='generator_parameters',
            field=models.TextField(blank=True, null=True, verbose_name='Generator Parameters'),
        ),
    ]
