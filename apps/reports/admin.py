from django.contrib import admin
from .models import DailyReport, WeeklyReport, MainJob, MainJobOperation

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