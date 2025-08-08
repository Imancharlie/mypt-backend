from rest_framework import serializers
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import TokenUsage, UserAction, SystemMetrics
from apps.users.models import UserProfile
from apps.reports.models import DailyReport, WeeklyReport, AIEnhancementLog
from apps.companies.models import Company


class TokenUsageSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = TokenUsage
        fields = ['id', 'user', 'user_name', 'user_username', 'tokens_consumed', 
                 'enhancement_type', 'content_type', 'cost_estimate', 'created_at']
        read_only_fields = ['created_at']


class UserActionSerializer(serializers.ModelSerializer):
    admin_user_name = serializers.CharField(source='admin_user.get_full_name', read_only=True)
    target_user_name = serializers.CharField(source='target_user.get_full_name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = UserAction
        fields = ['id', 'admin_user', 'admin_user_name', 'target_user', 'target_user_name',
                 'action', 'action_display', 'reason', 'created_at']
        read_only_fields = ['created_at']


class SystemMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemMetrics
        fields = '__all__'
        read_only_fields = ['created_at']


class UserProfileSerializer(serializers.ModelSerializer):
    program_display = serializers.CharField(source='get_program_display', read_only=True)
    pt_phase_display = serializers.CharField(source='get_pt_phase_display', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['student_id', 'program', 'program_display', 'year_of_study', 'pt_phase', 
                 'pt_phase_display', 'department', 'supervisor_name', 'supervisor_email', 
                 'phone_number', 'company_name', 'company_region']


class EnhancedUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    status_display = serializers.SerializerMethodField()
    last_login_formatted = serializers.SerializerMethodField()
    date_joined_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 
                 'is_staff', 'is_superuser', 'date_joined', 'last_login', 'profile',
                 'status_display', 'last_login_formatted', 'date_joined_formatted']
    
    def get_status_display(self, obj):
        return 'Active' if obj.is_active else 'Inactive'
    
    def get_last_login_formatted(self, obj):
        if obj.last_login:
            return obj.last_login.strftime('%Y-%m-%d %H:%M')
        return 'Never'
    
    def get_date_joined_formatted(self, obj):
        return obj.date_joined.strftime('%Y-%m-%d')


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    new_users_this_week = serializers.IntegerField()
    new_users_this_month = serializers.IntegerField()
    total_daily_reports = serializers.IntegerField()
    total_weekly_reports = serializers.IntegerField()
    reports_this_week = serializers.IntegerField()
    reports_this_month = serializers.IntegerField()
    total_companies = serializers.IntegerField()
    active_companies = serializers.IntegerField()
    total_tokens_used = serializers.IntegerField()
    tokens_this_week = serializers.IntegerField()
    tokens_this_month = serializers.IntegerField()


class UserManagementSerializer(serializers.Serializer):
    """Serializer for user management data"""
    users = EnhancedUserSerializer(many=True)
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    new_users_today = serializers.IntegerField()
    new_users_week = serializers.IntegerField()
    pagination = serializers.DictField()


class TokenAnalyticsSerializer(serializers.Serializer):
    """Serializer for token analytics data"""
    daily_usage = serializers.ListField()
    user_usage = serializers.ListField()
    enhancement_usage = serializers.ListField()
    content_usage = serializers.ListField()
    total_tokens = serializers.IntegerField()
    period_tokens = serializers.IntegerField()
    total_enhancements = serializers.IntegerField()
    period_enhancements = serializers.IntegerField()
    days = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class ReportAnalyticsSerializer(serializers.Serializer):
    """Serializer for report analytics data"""
    daily_reports_stats = serializers.ListField()
    weekly_reports_stats = serializers.ListField()
    user_report_activity = serializers.ListField()
    total_weekly_reports = serializers.IntegerField()
    completed_weekly_reports = serializers.IntegerField()
    completion_rate = serializers.FloatField()
    program_stats = serializers.ListField()
    days = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class ProgramStatsSerializer(serializers.Serializer):
    """Serializer for program statistics"""
    program = serializers.CharField()
    count = serializers.IntegerField()
    program_display = serializers.CharField()


class IndustryStatsSerializer(serializers.Serializer):
    """Serializer for industry statistics"""
    industry_type = serializers.CharField()
    count = serializers.IntegerField()
    industry_display = serializers.CharField()


class RecentActivitySerializer(serializers.Serializer):
    """Serializer for recent activity data"""
    recent_users = EnhancedUserSerializer(many=True)
    recent_reports = serializers.ListField()
    recent_ai_logs = serializers.ListField()
    recent_actions = UserActionSerializer(many=True)
    program_stats = ProgramStatsSerializer(many=True)
    industry_stats = IndustryStatsSerializer(many=True)


class UserSearchSerializer(serializers.Serializer):
    """Serializer for user search parameters"""
    search = serializers.CharField(required=False, allow_blank=True)
    program_filter = serializers.CharField(required=False, allow_blank=True)
    status_filter = serializers.CharField(required=False, allow_blank=True)
    date_filter = serializers.CharField(required=False, allow_blank=True)
    page = serializers.IntegerField(required=False, default=1)


class UserActionRequestSerializer(serializers.Serializer):
    """Serializer for user action requests"""
    user_ids = serializers.ListField(child=serializers.IntegerField())
    action = serializers.ChoiceField(choices=UserAction.ACTION_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)


class TokenUsageStatsSerializer(serializers.Serializer):
    """Serializer for token usage statistics"""
    total_tokens = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_tokens_per_user = serializers.FloatField()
    top_users = serializers.ListField()
    enhancement_type_breakdown = serializers.ListField()
    content_type_breakdown = serializers.ListField()
    daily_usage_trend = serializers.ListField() 