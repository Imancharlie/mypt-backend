from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import TokenUsage, UserAction, SystemMetrics
from apps.users.models import UserProfile
from apps.reports.models import DailyReport, WeeklyReport, AIEnhancementLog
from apps.companies.models import Company


class TokenUsageAdmin(admin.ModelAdmin):
    list_display = ['user', 'tokens_consumed', 'enhancement_type', 'content_type', 'cost_estimate', 'created_at']
    list_filter = ['enhancement_type', 'content_type', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


class UserActionAdmin(admin.ModelAdmin):
    list_display = ['admin_user', 'action', 'target_user', 'reason', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['admin_user__username', 'target_user__username', 'reason']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('admin_user', 'target_user')


class SystemMetricsAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_users', 'total_reports', 'total_companies', 'total_tokens_used', 'total_cost']
    list_filter = ['date']
    readonly_fields = ['created_at']
    ordering = ['-date']


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ['student_id', 'program', 'year_of_study', 'pt_phase', 'department', 
              'supervisor_name', 'supervisor_email', 'phone_number', 'company_name', 'company_region']


class EnhancedUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 
                   'get_student_id', 'get_program', 'get_registration_date', 'get_last_login', 'get_status_badge')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined', 'last_login', 
                  'profile__program', 'profile__pt_phase')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'profile__student_id')
    list_editable = ('is_active',)
    actions = ['ban_users', 'unban_users', 'delete_users', 'activate_users']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    def get_student_id(self, obj):
        return obj.profile.student_id if hasattr(obj, 'profile') and obj.profile.student_id else '-'
    get_student_id.short_description = 'Student ID'
    
    def get_program(self, obj):
        return obj.profile.get_program_display() if hasattr(obj, 'profile') and obj.profile.program else '-'
    get_program.short_description = 'Program'
    
    def get_registration_date(self, obj):
        return obj.date_joined.strftime('%Y-%m-%d') if obj.date_joined else '-'
    get_registration_date.short_description = 'Registered'
    
    def get_last_login(self, obj):
        return obj.last_login.strftime('%Y-%m-%d %H:%M') if obj.last_login else 'Never'
    get_last_login.short_description = 'Last Login'
    
    def get_status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        else:
            return format_html('<span style="color: red;">✗ Inactive</span>')
    get_status_badge.short_description = 'Status'
    
    def ban_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        for user in queryset:
            UserAction.objects.create(
                admin_user=request.user,
                target_user=user,
                action='BAN',
                reason='Banned by admin'
            )
        self.message_user(request, f'{updated} users have been banned.')
    ban_users.short_description = "Ban selected users"
    
    def unban_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        for user in queryset:
            UserAction.objects.create(
                admin_user=request.user,
                target_user=user,
                action='UNBAN',
                reason='Unbanned by admin'
            )
        self.message_user(request, f'{updated} users have been unbanned.')
    unban_users.short_description = "Unban selected users"
    
    def delete_users(self, request, queryset):
        for user in queryset:
            UserAction.objects.create(
                admin_user=request.user,
                target_user=user,
                action='DELETE',
                reason='Deleted by admin'
            )
        updated = queryset.delete()[0]
        self.message_user(request, f'{updated} users have been deleted.')
    delete_users.short_description = "Delete selected users"
    
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        for user in queryset:
            UserAction.objects.create(
                admin_user=request.user,
                target_user=user,
                action='ACTIVATE',
                reason='Activated by admin'
            )
        self.message_user(request, f'{updated} users have been activated.')
    activate_users.short_description = "Activate selected users"


class EnhancedDailyReportAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'week_number', 'hours_spent', 'get_description_preview', 'created_at']
    list_filter = ['week_number', 'date', 'student', 'created_at']
    search_fields = ['student__username', 'student__first_name', 'student__last_name', 'description']
    ordering = ['-date']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_description_preview(self, obj):
        return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
    get_description_preview.short_description = 'Description Preview'


class EnhancedWeeklyReportAdmin(admin.ModelAdmin):
    list_display = ['student', 'week_number', 'start_date', 'end_date', 'total_hours', 'is_complete', 'created_at']
    list_filter = ['week_number', 'is_complete', 'student', 'created_at']
    search_fields = ['student__username', 'student__first_name', 'student__last_name']
    ordering = ['-week_number']
    readonly_fields = ['created_at', 'updated_at']


class EnhancedCompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'industry_type', 'contact_person', 'phone', 'email', 'is_active', 'created_at']
    list_filter = ['industry_type', 'is_active', 'established_year', 'created_at']
    search_fields = ['name', 'contact_person', 'email', 'address']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
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


class AIEnhancementLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'content_type', 'enhancement_type', 'tokens_consumed', 'created_at']
    list_filter = ['content_type', 'enhancement_type', 'created_at']
    search_fields = ['user__username', 'original_content', 'enhanced_content']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


# Register the enhanced admin classes
admin.site.unregister(User)
admin.site.register(User, EnhancedUserAdmin)
admin.site.register(TokenUsage, TokenUsageAdmin)
admin.site.register(UserAction, UserActionAdmin)
admin.site.register(SystemMetrics, SystemMetricsAdmin)

# Re-register with enhanced admin classes
admin.site.unregister(DailyReport)
admin.site.register(DailyReport, EnhancedDailyReportAdmin)
admin.site.unregister(WeeklyReport)
admin.site.register(WeeklyReport, EnhancedWeeklyReportAdmin)
admin.site.unregister(Company)
admin.site.register(Company, EnhancedCompanyAdmin)
admin.site.register(AIEnhancementLog, AIEnhancementLogAdmin) 