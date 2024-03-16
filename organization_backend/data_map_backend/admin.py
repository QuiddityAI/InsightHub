import json
import logging
import os
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.forms import Textarea
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin  # type: ignore

from djangoql.admin import DjangoQLSearchMixin
import requests
from simple_history.admin import SimpleHistoryAdmin
from jsonsuit.widgets import JSONSuit
from django_object_actions import DjangoObjectActions, action
from import_export.admin import ImportExportMixin

from .data_backend_client import data_backend_url

from .models import DatasetSpecificSettingsOfCollection, EmbeddingSpace, FieldType, Generator, ImportConverter, Organization, Dataset, ObjectField, SearchHistoryItem, StoredMap, DataCollection, CollectionItem, TrainedClassifier, CollectionChat
from .utils import get_vector_field_dimensions
from .import_export import UserResource

admin.site.site_header = 'Quiddity'
admin.site.site_title = 'Quiddity'


class UserAdmin(ImportExportMixin, UserAdmin):
    resource_class = UserResource
    pass

admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(EmbeddingSpace)
class EmbeddingSpaceAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'name', 'dimensions')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    ordering = ['name']

    readonly_fields = ('changed_at', 'created_at')

    fields = ["name", "dimensions", "created_at", "changed_at"]


@admin.register(Generator)
class GeneratorAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'name', 'embedding_space', 'requires_context', 'text_similarity_threshold', 'image_similarity_threshold')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    ordering = ['name']

    readonly_fields = ('changed_at', 'created_at')

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2})},
        models.JSONField: {'widget': JSONSuit },
    }


class DatasetInline(admin.TabularInline):
    model = Dataset
    list_display_links = ('id', 'name')
    readonly_fields = ('changed_at', 'created_at', 'name')
    show_change_link = True
    extra = 0
    fields = ('id', 'name')


@admin.register(Organization)
class OrganizationAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    ordering = ['name']

    readonly_fields = ('changed_at', 'created_at')
    inlines = [DatasetInline]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # only show datasets of same organization for default_dataset_selection:
        if db_field.name == "default_dataset_selection":
            try:
                organization_id = int(request.path.split("/")[-3])  # type: ignore
            except ValueError:
                kwargs["queryset"] = Dataset.objects.filter(organization = -1)
            else:
                kwargs["queryset"] = Dataset.objects.filter(organization = organization_id)
        return super(OrganizationAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(ImportConverter)
class ImportConverterAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name', 'description')
    ordering = ['name']

    readonly_fields = ('changed_at', 'created_at')

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2})},
        models.JSONField: {'widget': JSONSuit },
    }


class ObjectFieldInline(admin.StackedInline):
    model = ObjectField
    readonly_fields = ('changed_at', 'created_at', 'action_buttons', 'items_having_value_count')
    extra = 0

    fields = [
        "identifier", "description",
        "field_type", "is_array", "language_analysis", "embedding_space", "index_parameters",
        "is_available_for_search", "text_similarity_threshold", "image_similarity_threshold",
        "is_available_for_filtering",
        "generator", "generator_parameters", "generating_condition",
        "source_fields", "should_be_generated",
        'items_having_value_count',
        'action_buttons',
    ]

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2})},
        models.JSONField: {'widget': JSONSuit },
    }

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # only show fields of same dataset for source fields:
        if db_field.name == "source_fields":
            try:
                dataset_id = int(request.path.split("/")[-3])  # type: ignore
            except ValueError:
                kwargs["queryset"] = ObjectField.objects.filter(dataset = -1)
            else:
                kwargs["queryset"] = ObjectField.objects.filter(dataset = dataset_id)
        return super(ObjectFieldInline, self).formfield_for_manytomany(db_field, request, **kwargs)

    def action_buttons(self, obj):
        return mark_safe(f'<button type=button class="btn-danger" onclick="window.location.href=\'/admin/data_map_backend/objectfield/{obj.id}/actions/delete_content/\';">Delete Content</button> \
                         <button type=button class="btn-info" onclick="window.location.href=\'/admin/data_map_backend/objectfield/{obj.id}/actions/generate_missing_values/\';">Generate Missing Values</button>')
    action_buttons.short_description = "Actions"


@admin.register(Dataset)
class DatasetAdmin(DjangoQLSearchMixin, DjangoObjectActions, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'organization', 'name', 'is_public', 'is_template')
    list_display_links = ('id', 'name')
    search_fields = ('name', 'organization')
    ordering = ['organization', 'name']

    readonly_fields = ('id', 'changed_at', 'created_at', 'get_field_overview_table_html',
                       'item_count', 'random_item', 'action_buttons')

    fields = [
        "id", "name", "entity_name", "entity_name_plural", "short_description",
        "is_template", "origin_template", "organization", "is_public", "admins",
        "source_plugin", "source_plugin_parameters",
        "database_name", "primary_key", "thumbnail_image",
        "descriptive_text_fields", "default_search_fields", "defaults",
        "applicable_import_converters",
        "item_count", "get_field_overview_table_html",
        "result_list_rendering", "collection_item_rendering",
        "hover_label_rendering", "detail_view_rendering", "statistics",
        "random_item",
        "created_at", "changed_at",
        'action_buttons',
    ]

    inlines = [
        ObjectFieldInline,
    ]

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2})},
        models.JSONField: {'widget': JSONSuit }
    }

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # only show fields of same dataset for source fields:
        if db_field.name in ["primary_key", "thumbnail_image"]:
            try:
                dataset_id = int(request.path.split("/")[-3])  # type: ignore
            except ValueError:
                kwargs["queryset"] = ObjectField.objects.filter(dataset = -1)
            else:
                kwargs["queryset"] = ObjectField.objects.filter(dataset = dataset_id)
        return super(DatasetAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # only show fields of same dataset for source fields:
        if db_field.name in ["descriptive_text_fields", "default_search_fields"]:
            try:
                dataset_id = int(request.path.split("/")[-3])  # type: ignore
            except ValueError:
                kwargs["queryset"] = ObjectField.objects.filter(dataset = -1)
            else:
                kwargs["queryset"] = ObjectField.objects.filter(dataset = dataset_id)
        return super(DatasetAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def get_field_overview_table_html(self, obj):
        try:
            header = ["Type", "Identifier", "Search / Filter / Generated", "Generator", "#"]
            html = """<table style='border: 1px solid; border-collapse: collapse;'>\n<tr>"""
            for item in header:
                html += f"<th style='border: 1px solid;'>{item}</th>\n"
            html += "</tr>\n"

            for field in obj.object_fields.all():
                html += "<tr style='border: 1px solid;'>\n"
                html += f"<td style='border: 1px solid; padding-right: 4px;'>{field.field_type + ('[]' if field.is_array else '') + (' ' + field.language_analysis if field.language_analysis else '')}</td>\n"
                html += f"<td style='border: 1px solid; padding-right: 4px;'><a href=\"/org/admin/data_map_backend/objectfield/{field.id}/change/\">{field.identifier} {'<i>(PK)</i>' if obj.primary_key == field else ''}</a></td>\n"
                thresholds = f"{field.text_similarity_threshold if field.text_similarity_threshold is not None else ''}"
                thresholds += f" {field.image_similarity_threshold if field.image_similarity_threshold is not None else ''}"
                attributes = f"{'s' if field.is_available_for_search else '-'} {thresholds} | {'f' if field.is_available_for_filtering else '-'} | {'g' if field.should_be_generated else '-'}"
                html += f"<td style='border: 1px solid;'>{attributes}</td>\n"
                html += f"<td style='border: 1px solid;'>{field.generator or ''}</td>\n"
                html += f"<td style='border: 1px solid;' align='right'>{field.items_having_value_count}</td>\n"
                html += "</tr>\n"

            html += "</table>"

            total_items = obj.item_count
            if total_items:
                for field in obj.object_fields.all():
                    if field.field_type != FieldType.VECTOR:
                        continue
                    dimensions = get_vector_field_dimensions(field)
                    if not dimensions:
                        continue
                    bytes_per_vector = 4
                    space_needed_gb = (dimensions * bytes_per_vector * total_items) / 1024 / 1024 / 1024
                    html += f"<br>Space needed for field '{field.identifier}': {space_needed_gb:.1f} GB"
        except Exception as e:
            return repr(e)
        return mark_safe(html)

    get_field_overview_table_html.short_description='Field Overview'

    def action_buttons(self, obj):
        return mark_safe(f'<button type=button class="btn-info" onclick="window.location.href=\'/admin/data_map_backend/dataset/{obj.id}/actions/update_database_layout/\';">Update Database Layout</button>')
    action_buttons.short_description = "Actions"

    @action(label="Update Database Layout", description="Update Database Layout")
    def update_database_layout(self, request, obj):
        url = data_backend_url + '/data_backend/update_database_layout'
        data = {
            'dataset_id': obj.id,
        }
        requests.post(url, json=data)
        self.message_user(request, "Updated the database layout")

    change_actions = ('update_database_layout',)

    def duplicate_datasets(self, request, queryset):
        for object in queryset:
            original_id = object.id
            original_descriptive_text_fields = object.descriptive_text_fields.all()
            original_default_search_fields = object.default_search_fields.all()
            object.id = None
            object.save()
            field_name_to_sink = {}
            for field in ObjectField.objects.filter(dataset = original_id):
                is_pk = field == object.primary_key
                is_thumbnail =  field == object.thumbnail_image
                is_descriptive = field in original_descriptive_text_fields
                is_default = field in original_default_search_fields
                source_fields = field.source_fields.all()
                field.id = None  # type: ignore
                field.dataset = object
                field.save()
                for source_field in source_fields:
                    field_name_to_sink[source_field.identifier] = field
                if is_pk:
                    object.primary_key = field
                if is_thumbnail:
                    object.thumbnail_image = field
                if is_descriptive:
                    object.descriptive_text_fields.add(field)
                if is_default:
                    object.default_search_fields.add(field)
            for field in ObjectField.objects.filter(dataset = object):
                if field.identifier in field_name_to_sink:
                    sink_field = field_name_to_sink[field.identifier]
                    sink_field.source_fields.add(field)
                    sink_field.save()
            object.save()
    duplicate_datasets.short_description = "Duplicate Datasets"

    actions = ['duplicate_datasets']

    class Media:
        js = ('hide_objectfield_parameters.js',)


@admin.register(ObjectField)
class ObjectFieldAdmin(DjangoQLSearchMixin, DjangoObjectActions, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'dataset', 'identifier', 'field_type', 'description')
    list_display_links = ('id', 'identifier')
    search_fields = ('identifier', 'description')
    ordering = ['dataset', 'identifier']

    readonly_fields = ('changed_at', 'created_at', 'items_having_value_count')

    @action(label="Delete Content", description="Delete field data and index")
    def delete_content(self, request, obj):
        # http://localhost:55125/admin/data_map_backend/objectfield/27/actions/delete_content/
        url = data_backend_url + '/data_backend/delete_field'
        data = {
            'dataset_id': obj.dataset_id,
            'field_identifier': obj.identifier,
        }
        requests.post(url, json=data)
        self.message_user(request, "Deleted this fields content")

    @action(label="Generate Missing Values", description="Generate missing values")
    def generate_missing_values(self, request, obj):
        url = data_backend_url + '/data_backend/generate_missing_values'
        data = {
            'dataset_id': obj.dataset_id,
            'field_identifier': obj.identifier,
        }
        requests.post(url, json=data)
        self.message_user(request, "Now generating missing values...")

    change_actions = ('delete_content', 'generate_missing_values')


@admin.register(SearchHistoryItem)
class SearchHistoryItemAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    ordering = ['name']
    readonly_fields = ('changed_at', 'created_at')

    formfield_overrides = {
        models.JSONField: {'widget': JSONSuit },
    }


@admin.register(StoredMap)
class StoredMapAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    ordering = ['name']
    readonly_fields = ('changed_at', 'created_at')


@admin.register(DatasetSpecificSettingsOfCollection)
class DatasetSpecificSettingsOfCollectionAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'collection', 'dataset')
    list_display_links = ('id',)
    search_fields = ('collection', 'dataset',)
    ordering = ['collection', 'dataset']
    readonly_fields = ('changed_at', 'created_at')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # only show fields of same dataset for source fields:
        if db_field.name in ["positive_annotation_field", "negative_annotation_field"]:
            try:
                item_id = int(request.path.split("/")[-3])  # type: ignore
            except ValueError:
                kwargs["queryset"] = ObjectField.objects.filter(dataset = -1)
            else:
                dataset_id = DatasetSpecificSettingsOfCollection.objects.get(id = item_id).dataset_id  # type: ignore
                kwargs["queryset"] = ObjectField.objects.filter(dataset = dataset_id)
        return super(DatasetSpecificSettingsOfCollectionAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # only show fields of same dataset for source fields:
        if db_field.name in ["relevant_object_fields"]:
            try:
                item_id = int(request.path.split("/")[-3])  # type: ignore
            except ValueError:
                kwargs["queryset"] = ObjectField.objects.filter(dataset = -1)
            else:
                dataset_id = DatasetSpecificSettingsOfCollection.objects.get(id = item_id).dataset_id  # type: ignore
                kwargs["queryset"] = ObjectField.objects.filter(dataset = dataset_id)
        return super(DatasetSpecificSettingsOfCollectionAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)


class DatasetSpecificSettingsOfCollectionInline(admin.StackedInline):
    model = DatasetSpecificSettingsOfCollection
    show_change_link = True
    readonly_fields = ('changed_at', 'created_at', 'link_to_change_view')
    extra = 0

    def link_to_change_view(self, obj):
        return mark_safe(f'<a href="/org/admin/data_map_backend/datasetspecificsettingsofcollection/{obj.id}/change/">Open Details</a>')

    link_to_change_view.short_description='Details'


@admin.register(CollectionItem)
class CollectionItemAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False
    list_display = ('id', 'collection', 'classes', 'date_added')
    list_display_links = ('id', 'classes')
    search_fields = ('id', 'collection', 'classes')
    ordering = ['collection', 'classes', 'date_added']
    readonly_fields = ('changed_at', 'date_added')

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2, 'cols': 30})},
        models.JSONField: {'widget': Textarea(attrs={'rows': 2, 'cols': 20})},
    }


class CollectionItemInline(admin.TabularInline):
    model = CollectionItem
    readonly_fields = ('date_added',)
    ordering = ['classes', 'date_added']
    extra = 0
    max_num = 100

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2, 'cols': 30})},
        models.JSONField: {'widget': Textarea(attrs={'rows': 2, 'cols': 20})},
    }


@admin.register(TrainedClassifier)
class TrainedClassifierAdmin(DjangoQLSearchMixin, DjangoObjectActions, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'collection', 'class_name', 'embedding_space')
    list_display_links = ('id', 'collection', 'class_name', 'embedding_space')
    search_fields = ('id', 'collection', 'class_name', 'embedding_space')
    ordering = ['collection', 'class_name', 'embedding_space']
    readonly_fields = ('changed_at', 'created_at', 'last_retrained_at', 'is_up_to_date', 'decision_vector_stats', 'get_retraining_status')
    exclude = ('decision_vector',)

    formfield_overrides = {
        models.JSONField: {'widget': JSONSuit },
    }

    def get_retraining_status(self, obj):
        try:
            url = data_backend_url + f'/data_backend/classifier/retraining_status'  # type: ignore
            data = {
                'collection_id': obj.collection_id,
                'class_name': obj.class_name,
                'embedding_space_id': obj.embedding_space_id,
            }
            result = requests.post(url, json=data)
        except Exception as e:
            return repr(e)
        try:
            data = result.json()
            if not data:
                return "Not currently training"
            return mark_safe(json.dumps(data, indent=2, ensure_ascii=False).replace(" ", "&nbsp").replace("\n", "<br>"))
        except requests.exceptions.JSONDecodeError:
            return "Not currently training"
    get_retraining_status.short_description = "Retraining status"  # type: ignore

    @action(label="(Re)train Classifier", description="Train classifier for this class and embedding space")
    def retrain_classifier(self, request, obj):
        url = data_backend_url + f'/data_backend/classifier/retrain'
        data = {
            'collection_id': obj.collection_id,
            'class_name': obj.class_name,
            'embedding_space_id': obj.embedding_space_id,
        }
        requests.post(url, json=data)
        self.message_user(request, "Retraining classifier...")

    change_actions = ('retrain_classifier',)

    def retrain_multiple_classifiers(self, request, queryset):
        for obj in queryset:
            url = data_backend_url + f'/data_backend/classifier/{obj.collection_id}/retrain'
            data = {
                'class_name': obj.class_name,
                'embedding_space_id': obj.embedding_space_id,
            }
            requests.post(url, json=data)

    actions = ['retrain_multiple_classifiers']


class TrainedClassifierInline(admin.StackedInline):
    model = TrainedClassifier
    readonly_fields = ('changed_at', 'created_at', 'last_retrained_at', 'is_up_to_date', 'decision_vector_stats', 'link_to_change_view')
    exclude = ('decision_vector',)
    extra = 0

    formfield_overrides = {
        models.JSONField: {'widget': JSONSuit },
    }

    def link_to_change_view(self, obj):
        return mark_safe(f'<a href="/org/admin/data_map_backend/trainedclassifier/{obj.id}/change/">Open Details</a>')

    link_to_change_view.short_description='Details'


@admin.register(DataCollection)
class DataCollectionAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'related_organization', 'name', 'created_by', 'is_public')
    list_display_links = ('id', 'name')
    search_fields = ('name', 'related_organization')
    ordering = ['related_organization', 'name']
    readonly_fields = ('changed_at', 'created_at', 'actual_classes_formatted')

    inlines = [
        DatasetSpecificSettingsOfCollectionInline,
        CollectionItemInline,
        TrainedClassifierInline,
    ]

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2})},
        models.JSONField: {'widget': JSONSuit }
    }


@admin.register(CollectionChat)
class CollectionChatAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name')
    ordering = ['id']
    readonly_fields = ('changed_at', 'created_at')

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2})},
        models.JSONField: {'widget': JSONSuit }
    }
