# Generated by Django 4.2.5 on 2023-09-06 20:26

import data_map_backend.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import simple_history.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmbeddingSpace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('created_at', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(auto_now=True, verbose_name='Changed at')),
            ],
            options={
                'verbose_name': 'Embedding Space',
                'verbose_name_plural': 'Embedding Spaces',
            },
        ),
        migrations.CreateModel(
            name='Generator',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('identifier', models.CharField(max_length=200, verbose_name='Identifier')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('created_at', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(auto_now=True, verbose_name='Changed at')),
                ('requires_context', models.BooleanField(default=False, verbose_name='Requires context')),
                ('parameter_description', models.TextField(blank=True, null=True, verbose_name='Parameter Description')),
                ('input_type', models.CharField(choices=[('TEXT', 'Text'), ('IDENTIFIER', 'Identifier'), ('FLOAT', 'Float'), ('INTEGER', 'Integer'), ('DATE', 'Date'), ('DATETIME', 'Datetime'), ('TIME', 'Time'), ('VECTOR', 'Vector'), ('CLASS_PROBABILITY', 'Class Probability'), ('FACE', 'Face'), ('URL', 'URL'), ('GEO_COORDINATES', 'Geo Coordinates'), ('TAG', 'Tag'), ('IMAGE', 'Image'), ('AUDIO', 'Audio'), ('VIDEO', 'Video'), ('FOREIGN_KEY', 'Reference to other element'), ('BOOL', 'Bool')], default='TEXT', max_length=50, verbose_name='Input Type')),
                ('input_is_array', models.BooleanField(default=False, verbose_name='Input is array / can be multiple')),
                ('input_description', models.TextField(blank=True, null=True, verbose_name='Input Description')),
                ('output_type', models.CharField(choices=[('TEXT', 'Text'), ('IDENTIFIER', 'Identifier'), ('FLOAT', 'Float'), ('INTEGER', 'Integer'), ('DATE', 'Date'), ('DATETIME', 'Datetime'), ('TIME', 'Time'), ('VECTOR', 'Vector'), ('CLASS_PROBABILITY', 'Class Probability'), ('FACE', 'Face'), ('URL', 'URL'), ('GEO_COORDINATES', 'Geo Coordinates'), ('TAG', 'Tag'), ('IMAGE', 'Image'), ('AUDIO', 'Audio'), ('VIDEO', 'Video'), ('FOREIGN_KEY', 'Reference to other element'), ('BOOL', 'Bool')], default='VECTOR', max_length=50, verbose_name='Output Type')),
                ('output_is_array', models.BooleanField(default=False, verbose_name='Output is array / can be multiple')),
                ('output_description', models.TextField(blank=True, null=True, verbose_name='Output Description')),
                ('embedding_space', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='data_map_backend.embeddingspace', verbose_name='Embedding Space')),
            ],
            options={
                'verbose_name': 'Generator',
                'verbose_name_plural': 'Generators',
            },
        ),
        migrations.CreateModel(
            name='ObjectField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identifier', models.CharField(max_length=200, verbose_name='Identifier')),
                ('created_at', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(auto_now=True, verbose_name='Changed at')),
                ('description', models.CharField(blank=True, max_length=200, null=True, verbose_name='Description')),
                ('field_type', models.CharField(choices=[('TEXT', 'Text'), ('IDENTIFIER', 'Identifier'), ('FLOAT', 'Float'), ('INTEGER', 'Integer'), ('DATE', 'Date'), ('DATETIME', 'Datetime'), ('TIME', 'Time'), ('VECTOR', 'Vector'), ('CLASS_PROBABILITY', 'Class Probability'), ('FACE', 'Face'), ('URL', 'URL'), ('GEO_COORDINATES', 'Geo Coordinates'), ('TAG', 'Tag'), ('IMAGE', 'Image'), ('AUDIO', 'Audio'), ('VIDEO', 'Video'), ('FOREIGN_KEY', 'Reference to other element'), ('BOOL', 'Bool')], default='TEXT', max_length=50, verbose_name='Type')),
                ('is_array', models.BooleanField(default=False, verbose_name='Is array')),
                ('vector_size', models.IntegerField(blank=True, null=True, verbose_name='Vector Size')),
                ('is_available_for_search', models.BooleanField(default=False, verbose_name='Available for fuzzy text or vector search')),
                ('is_available_for_filtering', models.BooleanField(default=False, verbose_name='Available for filtering')),
                ('index_parameters', models.TextField(blank=True, null=True, verbose_name='Index Parameters')),
                ('generator_parameters', models.TextField(blank=True, null=True, verbose_name='Generator Parameters')),
                ('generating_condition', models.TextField(blank=True, null=True, verbose_name='Generating Condition')),
                ('should_be_generated', models.BooleanField(default=False, help_text='Should be generated for new elements and when source fields are updated, not automatically generated for exisitng elements', verbose_name='Should be generated')),
                ('generator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='data_map_backend.generator', verbose_name='Generator')),
            ],
            options={
                'verbose_name': 'Object Field',
                'verbose_name_plural': 'Object Fields',
            },
        ),
        migrations.CreateModel(
            name='ObjectSchema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('name_plural', models.CharField(max_length=200, verbose_name='Name (Plural)')),
                ('short_description', models.CharField(blank=True, max_length=200, null=True, verbose_name='Short Description')),
                ('created_at', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(auto_now=True, verbose_name='Changed at')),
                ('result_list_rendering', models.JSONField(blank=True, default=data_map_backend.models.get_default_result_list_rendering, null=True, verbose_name='Rendering (Result List)')),
                ('collection_list_rendering', models.JSONField(blank=True, default=data_map_backend.models.get_default_collection_list_rendering, null=True, verbose_name='Rendering (Collection List)')),
                ('hover_label_rendering', models.JSONField(blank=True, default=data_map_backend.models.get_default_hover_label_rendering, null=True, verbose_name='Rendering (Hover Label)')),
                ('detail_view_rendering', models.JSONField(blank=True, default=data_map_backend.models.get_default_detail_view_rendering, null=True, verbose_name='Rendering (Detail View)')),
                ('descriptive_text_fields', models.ManyToManyField(blank=True, help_text='For Word2Vec and Cluster Titles', null=True, related_name='+', to='data_map_backend.objectfield', verbose_name='Descriptive Text Fields')),
            ],
            options={
                'verbose_name': 'Object Schema',
                'verbose_name_plural': 'Object Schemas',
            },
        ),
        migrations.CreateModel(
            name='StoredMap',
            fields=[
                ('id', models.CharField(editable=False, max_length=50, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(auto_now=True, verbose_name='Changed at')),
                ('map_data', models.BinaryField(blank=True, null=True, verbose_name='Data')),
                ('schema', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='data_map_backend.objectschema', verbose_name='Schema')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Stored Map',
                'verbose_name_plural': 'Stored Maps',
            },
        ),
        migrations.CreateModel(
            name='SearchHistoryItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(auto_now=True, verbose_name='Changed at')),
                ('parameters', models.JSONField(blank=True, null=True, verbose_name='Parameters')),
                ('schema', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='data_map_backend.objectschema', verbose_name='Schema')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Search History Item',
                'verbose_name_plural': 'Search History Items',
            },
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('created_at', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(auto_now=True, verbose_name='Changed at')),
                ('members', models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL, verbose_name='Members')),
            ],
            options={
                'verbose_name': 'Organization',
                'verbose_name_plural': 'Organizations',
            },
        ),
        migrations.AddField(
            model_name='objectschema',
            name='organization',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='data_map_backend.organization', verbose_name='Organization'),
        ),
        migrations.AddField(
            model_name='objectschema',
            name='primary_key',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='data_map_backend.objectfield', verbose_name='Primary Key'),
        ),
        migrations.AddField(
            model_name='objectschema',
            name='thumbnail_image',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='data_map_backend.objectfield', verbose_name='Thumbnail Image'),
        ),
        migrations.AddField(
            model_name='objectfield',
            name='schema',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='object_fields', to='data_map_backend.objectschema', verbose_name='Schema'),
        ),
        migrations.AddField(
            model_name='objectfield',
            name='source_fields',
            field=models.ManyToManyField(blank=True, to='data_map_backend.objectfield', verbose_name='Source Fields'),
        ),
        migrations.CreateModel(
            name='ItemCollection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(auto_now=True, verbose_name='Changed at')),
                ('positive_ids', models.JSONField(default=list, verbose_name='Positive IDs')),
                ('negative_ids', models.JSONField(default=list, verbose_name='Negative IDs')),
                ('schema', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='data_map_backend.objectschema', verbose_name='Schema')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Item Collection',
                'verbose_name_plural': 'Item Collections',
            },
        ),
        migrations.CreateModel(
            name='HistoricalStoredMap',
            fields=[
                ('id', models.CharField(db_index=True, editable=False, max_length=50, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(blank=True, editable=False, verbose_name='Changed at')),
                ('map_data', models.BinaryField(blank=True, null=True, verbose_name='Data')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('schema', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='data_map_backend.objectschema', verbose_name='Schema')),
                ('user', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'historical Stored Map',
                'verbose_name_plural': 'historical Stored Maps',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalSearchHistoryItem',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(blank=True, editable=False, verbose_name='Changed at')),
                ('parameters', models.JSONField(blank=True, null=True, verbose_name='Parameters')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('schema', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='data_map_backend.objectschema', verbose_name='Schema')),
                ('user', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'historical Search History Item',
                'verbose_name_plural': 'historical Search History Items',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalOrganization',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('created_at', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(blank=True, editable=False, verbose_name='Changed at')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical Organization',
                'verbose_name_plural': 'historical Organizations',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalObjectSchema',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('name_plural', models.CharField(max_length=200, verbose_name='Name (Plural)')),
                ('short_description', models.CharField(blank=True, max_length=200, null=True, verbose_name='Short Description')),
                ('created_at', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(blank=True, editable=False, verbose_name='Changed at')),
                ('result_list_rendering', models.JSONField(blank=True, default=data_map_backend.models.get_default_result_list_rendering, null=True, verbose_name='Rendering (Result List)')),
                ('collection_list_rendering', models.JSONField(blank=True, default=data_map_backend.models.get_default_collection_list_rendering, null=True, verbose_name='Rendering (Collection List)')),
                ('hover_label_rendering', models.JSONField(blank=True, default=data_map_backend.models.get_default_hover_label_rendering, null=True, verbose_name='Rendering (Hover Label)')),
                ('detail_view_rendering', models.JSONField(blank=True, default=data_map_backend.models.get_default_detail_view_rendering, null=True, verbose_name='Rendering (Detail View)')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('organization', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='data_map_backend.organization', verbose_name='Organization')),
                ('primary_key', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='data_map_backend.objectfield', verbose_name='Primary Key')),
                ('thumbnail_image', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='data_map_backend.objectfield', verbose_name='Thumbnail Image')),
            ],
            options={
                'verbose_name': 'historical Object Schema',
                'verbose_name_plural': 'historical Object Schemas',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalObjectField',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('identifier', models.CharField(max_length=200, verbose_name='Identifier')),
                ('created_at', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(blank=True, editable=False, verbose_name='Changed at')),
                ('description', models.CharField(blank=True, max_length=200, null=True, verbose_name='Description')),
                ('field_type', models.CharField(choices=[('TEXT', 'Text'), ('IDENTIFIER', 'Identifier'), ('FLOAT', 'Float'), ('INTEGER', 'Integer'), ('DATE', 'Date'), ('DATETIME', 'Datetime'), ('TIME', 'Time'), ('VECTOR', 'Vector'), ('CLASS_PROBABILITY', 'Class Probability'), ('FACE', 'Face'), ('URL', 'URL'), ('GEO_COORDINATES', 'Geo Coordinates'), ('TAG', 'Tag'), ('IMAGE', 'Image'), ('AUDIO', 'Audio'), ('VIDEO', 'Video'), ('FOREIGN_KEY', 'Reference to other element'), ('BOOL', 'Bool')], default='TEXT', max_length=50, verbose_name='Type')),
                ('is_array', models.BooleanField(default=False, verbose_name='Is array')),
                ('vector_size', models.IntegerField(blank=True, null=True, verbose_name='Vector Size')),
                ('is_available_for_search', models.BooleanField(default=False, verbose_name='Available for fuzzy text or vector search')),
                ('is_available_for_filtering', models.BooleanField(default=False, verbose_name='Available for filtering')),
                ('index_parameters', models.TextField(blank=True, null=True, verbose_name='Index Parameters')),
                ('generator_parameters', models.TextField(blank=True, null=True, verbose_name='Generator Parameters')),
                ('generating_condition', models.TextField(blank=True, null=True, verbose_name='Generating Condition')),
                ('should_be_generated', models.BooleanField(default=False, help_text='Should be generated for new elements and when source fields are updated, not automatically generated for exisitng elements', verbose_name='Should be generated')),
                ('_order', models.IntegerField(editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('generator', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='data_map_backend.generator', verbose_name='Generator')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('schema', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='data_map_backend.objectschema', verbose_name='Schema')),
            ],
            options={
                'verbose_name': 'historical Object Field',
                'verbose_name_plural': 'historical Object Fields',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalItemCollection',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(blank=True, editable=False, verbose_name='Changed at')),
                ('positive_ids', models.JSONField(default=list, verbose_name='Positive IDs')),
                ('negative_ids', models.JSONField(default=list, verbose_name='Negative IDs')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('schema', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='data_map_backend.objectschema', verbose_name='Schema')),
                ('user', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'historical Item Collection',
                'verbose_name_plural': 'historical Item Collections',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalGenerator',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('identifier', models.CharField(max_length=200, verbose_name='Identifier')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('created_at', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(blank=True, editable=False, verbose_name='Changed at')),
                ('requires_context', models.BooleanField(default=False, verbose_name='Requires context')),
                ('parameter_description', models.TextField(blank=True, null=True, verbose_name='Parameter Description')),
                ('input_type', models.CharField(choices=[('TEXT', 'Text'), ('IDENTIFIER', 'Identifier'), ('FLOAT', 'Float'), ('INTEGER', 'Integer'), ('DATE', 'Date'), ('DATETIME', 'Datetime'), ('TIME', 'Time'), ('VECTOR', 'Vector'), ('CLASS_PROBABILITY', 'Class Probability'), ('FACE', 'Face'), ('URL', 'URL'), ('GEO_COORDINATES', 'Geo Coordinates'), ('TAG', 'Tag'), ('IMAGE', 'Image'), ('AUDIO', 'Audio'), ('VIDEO', 'Video'), ('FOREIGN_KEY', 'Reference to other element'), ('BOOL', 'Bool')], default='TEXT', max_length=50, verbose_name='Input Type')),
                ('input_is_array', models.BooleanField(default=False, verbose_name='Input is array / can be multiple')),
                ('input_description', models.TextField(blank=True, null=True, verbose_name='Input Description')),
                ('output_type', models.CharField(choices=[('TEXT', 'Text'), ('IDENTIFIER', 'Identifier'), ('FLOAT', 'Float'), ('INTEGER', 'Integer'), ('DATE', 'Date'), ('DATETIME', 'Datetime'), ('TIME', 'Time'), ('VECTOR', 'Vector'), ('CLASS_PROBABILITY', 'Class Probability'), ('FACE', 'Face'), ('URL', 'URL'), ('GEO_COORDINATES', 'Geo Coordinates'), ('TAG', 'Tag'), ('IMAGE', 'Image'), ('AUDIO', 'Audio'), ('VIDEO', 'Video'), ('FOREIGN_KEY', 'Reference to other element'), ('BOOL', 'Bool')], default='VECTOR', max_length=50, verbose_name='Output Type')),
                ('output_is_array', models.BooleanField(default=False, verbose_name='Output is array / can be multiple')),
                ('output_description', models.TextField(blank=True, null=True, verbose_name='Output Description')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('embedding_space', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='data_map_backend.embeddingspace', verbose_name='Embedding Space')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical Generator',
                'verbose_name_plural': 'historical Generators',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalEmbeddingSpace',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('created_at', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Created at')),
                ('changed_at', models.DateTimeField(blank=True, editable=False, verbose_name='Changed at')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical Embedding Space',
                'verbose_name_plural': 'historical Embedding Spaces',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.AlterOrderWithRespectTo(
            name='objectfield',
            order_with_respect_to='schema',
        ),
    ]
