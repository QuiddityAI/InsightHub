# Generated by Django 4.2.7 on 2024-02-18 10:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0016_historicalsearchhistoryitem_display_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalstoredmap',
            name='display_name',
            field=models.CharField(blank=True, help_text='Name to be displayed in the frontend, including HTML markup', max_length=300, null=True, verbose_name='Display Name'),
        ),
        migrations.AddField(
            model_name='storedmap',
            name='display_name',
            field=models.CharField(blank=True, help_text='Name to be displayed in the frontend, including HTML markup', max_length=300, null=True, verbose_name='Display Name'),
        ),
    ]
