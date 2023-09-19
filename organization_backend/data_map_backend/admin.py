import logging
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.forms import Textarea
from django.db import models

from djangoql.admin import DjangoQLSearchMixin
from simple_history.admin import SimpleHistoryAdmin
from jsonsuit.widgets import JSONSuit
from django_object_actions import DjangoObjectActions, action

from .models import EmbeddingSpace, Generator, Organization, ObjectSchema, ObjectField, SearchHistoryItem, ItemCollection, StoredMap

# admin.site.site_header = 'Site Header'


@admin.register(EmbeddingSpace)
class EmbeddingSpaceAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    ordering = ['name']

    readonly_fields = ('changed_at', 'created_at')


@admin.register(Generator)
class GeneratorAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'name', 'requires_context')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    ordering = ['name']

    readonly_fields = ('changed_at', 'created_at')


class ObjectSchemaInline(admin.TabularInline):
    model = ObjectSchema
    list_display_links = ('id', 'name_plural')
    readonly_fields = ('changed_at', 'created_at', 'name_plural')
    show_change_link = True
    extra = 0
    fields = ('id', 'name_plural')


@admin.register(Organization)
class OrganizationAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    ordering = ['name']

    readonly_fields = ('changed_at', 'created_at')
    inlines = [ObjectSchemaInline]


class ObjectFieldInline(admin.StackedInline):
    model = ObjectField
    readonly_fields = ('changed_at', 'created_at', 'button_delete_content', 'button_generate_missing_values')
    extra = 0

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2})},
    }

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # only show fields of same schema for source fields:
        if db_field.name == "source_fields":
            try:
                schema_id = int(request.path.split("/")[-3])
            except ValueError:
                kwargs["queryset"] = ObjectField.objects.filter(schema = -1)
            else:
                kwargs["queryset"] = ObjectField.objects.filter(schema = schema_id)
        return super(ObjectFieldInline, self).formfield_for_manytomany(db_field, request, **kwargs)

    def button_delete_content(self, obj):
        return mark_safe(f'<button type=button class="btn-danger" onclick="window.location.href=\'/admin/data_map_backend/objectfield/{obj.id}/actions/delete_content/\';">Delete Content</button>')
    button_delete_content.short_description = "Delete Content"

    def button_generate_missing_values(self, obj):
        return mark_safe(f'<button type=button class="btn-info" onclick="window.location.href=\'/admin/data_map_backend/objectfield/{obj.id}/actions/generate_missing_values/\';">Generate Missing Values</button>')
    button_generate_missing_values.short_description = "Generate Missing Values"


@admin.register(ObjectSchema)
class ObjectSchemaAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'organization', 'name_plural')
    list_display_links = ('id', 'name_plural')
    search_fields = ('name_plural', 'organization')
    ordering = ['organization', 'name_plural']

    readonly_fields = ('changed_at', 'created_at', 'get_field_overview_table_html')

    inlines = [
        ObjectFieldInline,
    ]

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2})},
        models.JSONField: {'widget': JSONSuit }
    }

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # only show fields of same schema for source fields:
        if db_field.name in ["primary_key", "thumbnail_image"]:
            try:
                schema_id = int(request.path.split("/")[-3])
            except ValueError:
                kwargs["queryset"] = ObjectField.objects.filter(schema = -1)
            else:
                kwargs["queryset"] = ObjectField.objects.filter(schema = schema_id)
        return super(ObjectSchemaAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # only show fields of same schema for source fields:
        if db_field.name in ["descriptive_text_fields", "default_search_fields"]:
            try:
                schema_id = int(request.path.split("/")[-3])
            except ValueError:
                kwargs["queryset"] = ObjectField.objects.filter(schema = -1)
            else:
                kwargs["queryset"] = ObjectField.objects.filter(schema = schema_id)
        return super(ObjectSchemaAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def get_field_overview_table_html(self, obj):
        header = ["Type", "Identifier", "Search / Filter / Generated", "Generator"]
        html = """<table style='border: 1px solid; border-collapse: collapse;'>\n<tr>"""
        for item in header:
            html += f"<th style='border: 1px solid;'>{item}</th>\n"
        html += "</tr>\n"

        for field in obj.object_fields.all():
            html += "<tr style='border: 1px solid;'>\n"
            html += f"<td style='border: 1px solid; padding-right: 4px;'>{field.field_type + ('[]' if field.is_array else '')}</td>\n"
            html += f"<td style='border: 1px solid; padding-right: 4px;'>{field.identifier} {'<i>(PK)</i>' if obj.primary_key == field else ''}</td>\n"
            attributes = f"{'s' if field.is_available_for_search else '-'} | {'f' if field.is_available_for_filtering else '-'} | {'g' if field.should_be_generated else '-'}"
            html += f"<td style='border: 1px solid;'>{attributes}</td>\n"
            html += f"<td style='border: 1px solid;'>{field.generator or ''}</td>\n"
            html += "</tr>\n"

        html += "</table>"
        return mark_safe(html)

    get_field_overview_table_html.short_description='Field Overview'


@admin.register(ObjectField)
class ObjectFieldAdmin(DjangoQLSearchMixin, DjangoObjectActions, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'field_type', 'identifier', 'description')
    list_display_links = ('id', 'identifier')
    search_fields = ('identifier', 'description')

    readonly_fields = ('changed_at', 'created_at')

    @action(label="Delete Content", description="Delete field data and index") # optional
    def delete_content(self, request, obj):
        # http://localhost:55125/admin/data_map_backend/objectfield/27/actions/delete_content/
        logging.warning("deleting field content")
        self.message_user(request, "deleting field content")

    @action(label="Generate Missing Values", description="Generate missing values") # optional
    def generate_missing_values(self, request, obj):
        logging.warning("generating missing values")
        self.message_user(request, "generating missing values")

    change_actions = ('delete_content', 'generate_missing_values')


@admin.register(SearchHistoryItem)
class SearchHistoryItemAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    ordering = ['name']
    readonly_fields = ('changed_at', 'created_at')


@admin.register(ItemCollection)
class ItemCollectionAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    ordering = ['name']
    readonly_fields = ('changed_at', 'created_at')


@admin.register(StoredMap)
class StoredMapAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    ordering = ['name']
    readonly_fields = ('changed_at', 'created_at')
