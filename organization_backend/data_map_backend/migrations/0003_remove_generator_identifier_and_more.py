# Generated by Django 4.2.5 on 2023-09-23 08:12

import data_map_backend.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data_map_backend', '0002_objectschema_default_search_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='generator',
            name='identifier',
        ),
        migrations.RemoveField(
            model_name='historicalgenerator',
            name='identifier',
        ),
        migrations.RemoveField(
            model_name='historicalobjectfield',
            name='vector_size',
        ),
        migrations.RemoveField(
            model_name='objectfield',
            name='vector_size',
        ),
        migrations.RemoveField(
            model_name='objectfield',
            name='generator_parameters',
        ),
        migrations.RemoveField(
            model_name='objectfield',
            name='index_parameters',
        ),
        migrations.RemoveField(
            model_name='historicalobjectfield',
            name='generator_parameters',
        ),
        migrations.RemoveField(
            model_name='historicalobjectfield',
            name='index_parameters',
        ),
        migrations.AddField(
            model_name='embeddingspace',
            name='dimensions',
            field=models.IntegerField(blank=True, help_text='Vector size of the embedding', null=True, verbose_name='Dimensions'),
        ),
        migrations.AddField(
            model_name='generator',
            name='default_parameters',
            field=models.JSONField(blank=True, null=True, verbose_name='Default Parameters'),
        ),
        migrations.AddField(
            model_name='generator',
            name='module',
            field=models.CharField(default='x', max_length=200, verbose_name='Module'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicalembeddingspace',
            name='dimensions',
            field=models.IntegerField(blank=True, help_text='Vector size of the embedding', null=True, verbose_name='Dimensions'),
        ),
        migrations.AddField(
            model_name='historicalgenerator',
            name='default_parameters',
            field=models.JSONField(blank=True, null=True, verbose_name='Default Parameters'),
        ),
        migrations.AddField(
            model_name='historicalgenerator',
            name='module',
            field=models.CharField(default='x', max_length=200, verbose_name='Module'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicalobjectfield',
            name='embedding_space',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text='If not set, embedding space of generator will be used', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='data_map_backend.embeddingspace', verbose_name='Embedding Space'),
        ),
        migrations.AddField(
            model_name='objectfield',
            name='embedding_space',
            field=models.ForeignKey(blank=True, help_text='If not set, embedding space of generator will be used', null=True, on_delete=django.db.models.deletion.PROTECT, to='data_map_backend.embeddingspace', verbose_name='Embedding Space'),
        ),
        migrations.AddField(
            model_name='historicalobjectfield',
            name='generator_parameters',
            field=models.JSONField(blank=True, null=True, verbose_name='Generator Parameters'),
        ),
        migrations.AddField(
            model_name='historicalobjectfield',
            name='index_parameters',
            field=models.JSONField(blank=True, null=True, verbose_name='Index Parameters'),
        ),
        migrations.AlterField(
            model_name='historicalobjectfield',
            name='is_available_for_search',
            field=models.BooleanField(default=False, verbose_name='Available for fulltext or vector search'),
        ),
        migrations.AlterField(
            model_name='historicalobjectfield',
            name='should_be_generated',
            field=models.BooleanField(default=False, help_text='Should be generated for new elements and when source fields are updated, not automatically generated for exisitng elements', verbose_name='Generate on insert / change'),
        ),
        migrations.AlterField(
            model_name='historicalobjectschema',
            name='collection_list_rendering',
            field=models.JSONField(blank=True, default=data_map_backend.models.get_default_collection_list_rendering, null=True, verbose_name='Collection List Rendering'),
        ),
        migrations.AlterField(
            model_name='historicalobjectschema',
            name='detail_view_rendering',
            field=models.JSONField(blank=True, default=data_map_backend.models.get_default_detail_view_rendering, null=True, verbose_name='Detail View Rendering'),
        ),
        migrations.AlterField(
            model_name='historicalobjectschema',
            name='hover_label_rendering',
            field=models.JSONField(blank=True, default=data_map_backend.models.get_default_hover_label_rendering, null=True, verbose_name='Hover Label Rendering'),
        ),
        migrations.AlterField(
            model_name='historicalobjectschema',
            name='result_list_rendering',
            field=models.JSONField(blank=True, default=data_map_backend.models.get_default_result_list_rendering, null=True, verbose_name='Result List Rendering'),
        ),
        migrations.AddField(
            model_name='objectfield',
            name='generator_parameters',
            field=models.JSONField(blank=True, null=True, verbose_name='Generator Parameters'),
        ),
        migrations.AddField(
            model_name='objectfield',
            name='index_parameters',
            field=models.JSONField(blank=True, null=True, verbose_name='Index Parameters'),
        ),
        migrations.AlterField(
            model_name='objectfield',
            name='is_available_for_search',
            field=models.BooleanField(default=False, verbose_name='Available for fulltext or vector search'),
        ),
        migrations.AlterField(
            model_name='objectfield',
            name='should_be_generated',
            field=models.BooleanField(default=False, help_text='Should be generated for new elements and when source fields are updated, not automatically generated for exisitng elements', verbose_name='Generate on insert / change'),
        ),
        migrations.AlterField(
            model_name='objectschema',
            name='collection_list_rendering',
            field=models.JSONField(blank=True, default=data_map_backend.models.get_default_collection_list_rendering, null=True, verbose_name='Collection List Rendering'),
        ),
        migrations.AlterField(
            model_name='objectschema',
            name='detail_view_rendering',
            field=models.JSONField(blank=True, default=data_map_backend.models.get_default_detail_view_rendering, null=True, verbose_name='Detail View Rendering'),
        ),
        migrations.AlterField(
            model_name='objectschema',
            name='hover_label_rendering',
            field=models.JSONField(blank=True, default=data_map_backend.models.get_default_hover_label_rendering, null=True, verbose_name='Hover Label Rendering'),
        ),
        migrations.AlterField(
            model_name='objectschema',
            name='result_list_rendering',
            field=models.JSONField(blank=True, default=data_map_backend.models.get_default_result_list_rendering, null=True, verbose_name='Result List Rendering'),
        ),
    ]
