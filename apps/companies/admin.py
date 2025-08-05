from django.contrib import admin
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry_type', 'contact_person', 'phone', 'email', 'is_active', 'created_at')
    list_filter = ('industry_type', 'is_active', 'established_year')
    search_fields = ('name', 'contact_person', 'email', 'address')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'industry_type', 'description')
        }),
        ('Contact Information', {
            'fields': ('address', 'contact_person', 'phone', 'email', 'website')
        }),
        ('Additional Information', {
            'fields': ('established_year', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ) 