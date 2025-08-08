from django.contrib import admin
from .models import DailyReport, WeeklyReport, MainJob, MainJobOperation, OriginalUserInputs

@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'week_number', 'hours_spent', 'created_at']
    list_filter = ['week_number', 'date', 'student']
    search_fields = ['student__username', 'description']
    ordering = ['-date']

@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ['student', 'week_number', 'start_date', 'end_date', 'total_hours', 'is_complete']
    list_filter = ['week_number', 'is_complete', 'student']
    search_fields = ['student__username']
    ordering = ['-week_number']

@admin.register(MainJob)
class MainJobAdmin(admin.ModelAdmin):
    list_display = ['title', 'weekly_report', 'created_at']
    list_filter = ['weekly_report__week_number', 'weekly_report__student']
    search_fields = ['title', 'description', 'weekly_report__student__username']
    ordering = ['-created_at']

@admin.register(MainJobOperation)
class MainJobOperationAdmin(admin.ModelAdmin):
    list_display = ['main_job', 'step_number', 'operation_description', 'created_at']
    list_filter = ['main_job__weekly_report__week_number', 'step_number']
    search_fields = ['operation_description', 'tools_used', 'main_job__title']
    ordering = ['main_job', 'step_number']

@admin.register(OriginalUserInputs)
class OriginalUserInputsAdmin(admin.ModelAdmin):
    list_display = ['user', 'week_number', 'get_user_program', 'get_company_name', 'original_main_job_title', 'get_daily_reports_count', 'get_operations_count', 'is_reset_available', 'created_at']
    list_filter = ['week_number', 'is_reset_available', 'user', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'original_main_job_title', 'enhancement_instructions']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'get_user_program', 'get_company_name', 'get_daily_reports_count', 'get_operations_count']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'week_number', 'get_user_program', 'get_company_name')
        }),
        ('Original Content', {
            'fields': ('original_main_job_title', 'original_daily_reports', 'original_operations')
        }),
        ('Enhancement Details', {
            'fields': ('enhancement_instructions', 'is_reset_available')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_user_program(self, obj):
        return obj.get_user_program()
    get_user_program.short_description = 'Program'
    
    def get_company_name(self, obj):
        return obj.get_company_name()
    get_company_name.short_description = 'Company'
    
    def get_daily_reports_count(self, obj):
        return obj.get_daily_reports_count()
    get_daily_reports_count.short_description = 'Daily Reports'
    
    def get_operations_count(self, obj):
        return obj.get_operations_count()
    get_operations_count.short_description = 'Operations' 