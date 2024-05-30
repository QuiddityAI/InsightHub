# Generated by Django 5.0.6 on 2024-05-30 16:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0007_dataset_schema_historicaldataset_schema_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasetspecificsettingsofcollection',
            name='positive_annotation_field',
            field=models.ForeignKey(blank=True, help_text='binary: bool field, exclusive: single tag, non-exclusive: tag array field', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='data_map_backend.datasetfield', verbose_name='Positive Annotation Field'),
        ),
        migrations.AlterField(
            model_name='datasetspecificsettingsofcollection',
            name='negative_annotation_field',
            field=models.ForeignKey(blank=True, help_text='binary: bool field, exclusive: single tag, non-exclusive: tag array field', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='data_map_backend.datasetfield', verbose_name='Negative Annotation Field'),
        ),
        migrations.AlterField(
            model_name='historicaldatasetspecificsettingsofcollection',
            name='positive_annotation_field',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text='binary: bool field, exclusive: single tag, non-exclusive: tag array field', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='data_map_backend.datasetfield', verbose_name='Positive Annotation Field'),
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='descriptive_text_fields',
        ),
        migrations.RemoveField(
            model_name='historicaldataset',
            name='primary_key',
        ),
        migrations.AlterField(
            model_name='historicaldatasetspecificsettingsofcollection',
            name='negative_annotation_field',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text='binary: bool field, exclusive: single tag, non-exclusive: tag array field', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='data_map_backend.datasetfield', verbose_name='Negative Annotation Field'),
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='primary_key',
        ),
        migrations.RemoveField(
            model_name='historicaldataset',
            name='thumbnail_image',
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='thumbnail_image',
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='default_search_fields',
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='applicable_export_converters',
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='applicable_import_converters',
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='detail_view_rendering',
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='entity_name',
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='entity_name_plural',
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='hover_label_rendering',
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='is_template',
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='origin_template',
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='result_list_rendering',
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='statistics',
        ),
        migrations.RemoveField(
            model_name='historicaldataset',
            name='detail_view_rendering',
        ),
        migrations.RemoveField(
            model_name='historicaldataset',
            name='entity_name',
        ),
        migrations.RemoveField(
            model_name='historicaldataset',
            name='entity_name_plural',
        ),
        migrations.RemoveField(
            model_name='historicaldataset',
            name='hover_label_rendering',
        ),
        migrations.RemoveField(
            model_name='historicaldataset',
            name='is_template',
        ),
        migrations.RemoveField(
            model_name='historicaldataset',
            name='origin_template',
        ),
        migrations.RemoveField(
            model_name='historicaldataset',
            name='result_list_rendering',
        ),
        migrations.RemoveField(
            model_name='historicaldataset',
            name='statistics',
        ),
        migrations.AlterField(
            model_name='datasetspecificsettingsofcollection',
            name='relevant_object_fields',
            field=models.ManyToManyField(blank=True, help_text="The 'source' fields (text or image) for items from this dataset, using default search fields (or their sources for vectors) if empty", related_name='+', to='data_map_backend.datasetfield', verbose_name='Relevant Object Fields'),
        ),
        migrations.DeleteModel(
            name='HistoricalObjectField',
        ),
        migrations.DeleteModel(
            name='ObjectField',
        ),
    ]
