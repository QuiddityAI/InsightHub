# Generated by Django 5.0.4 on 2024-04-27 14:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0010_delete_historicalsearchhistoryitem'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicaltrainedclassifier',
            name='collection',
        ),
        migrations.RemoveField(
            model_name='historicaltrainedclassifier',
            name='embedding_space',
        ),
        migrations.RemoveField(
            model_name='historicaltrainedclassifier',
            name='history_user',
        ),
        migrations.DeleteModel(
            name='HistoricalStoredMap',
        ),
        migrations.DeleteModel(
            name='HistoricalTrainedClassifier',
        ),
    ]
