from django.contrib import admin

from djangoql.admin import DjangoQLSearchMixin
from simple_history.admin import SimpleHistoryAdmin

from .models import Organization

# admin.site.site_header = 'Site Header'

@admin.register(Organization)
class OrganizationAdmin(DjangoQLSearchMixin, SimpleHistoryAdmin):
    djangoql_completion_enabled_by_default = False  # make normal search the default
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    readonly_fields = ('changed_at', 'created_at')
    fieldsets = (
        ("General", {
            'fields': (
                'name',
                'created_at',
                'changed_at',
                )
        }),
    )
