# Generated by Django 5.0.2 on 2024-02-22 11:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0024_rename_classifierexample_collectionitem'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='itemcollection',
            name='dataset',
        ),
        migrations.RemoveField(
            model_name='itemcollection',
            name='user',
        ),
        migrations.DeleteModel(
            name='HistoricalItemCollection',
        ),
        migrations.DeleteModel(
            name='ItemCollection',
        ),
    ]
