from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from .models import TokenUsage, UserAction, SystemMetrics
from .serializers import (
    TokenUsageSerializer, UserActionSerializer, SystemMetricsSerializer,
    EnhancedUserSerializer, DashboardStatsSerializer, UserManagementSerializer,
    TokenAnalyticsSerializer, ReportAnalyticsSerializer, UserSearchSerializer,
    UserActionRequestSerializer, TokenUsageStatsSerializer, RecentActivitySerializer
)
from apps.reports.models import DailyReport, WeeklyReport, AIEnhancementLog
from apps.companies.models import Company
from apps.users.models import UserProfile


class AdminPermission(permissions.BasePermission):
    """Custom permission for admin-only access"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff


@api_view(['GET'])
@permission_classes([AdminPermission])
def dashboard_stats(request):
    """Get dashboard statistics"""
    # Get date ranges
    today = timezone.now().date()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    
    # User statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    new_users_this_week = User.objects.filter(date_joined__gte=last_week).count()
    new_users_this_month = User.objects.filter(date_joined__gte=last_month).count()
    
    # Report statistics
    total_daily_reports = DailyReport.objects.count()
    total_weekly_reports = WeeklyReport.objects.count()
    reports_this_week = DailyReport.objects.filter(created_at__gte=last_week).count()
    reports_this_month = DailyReport.objects.filter(created_at__gte=last_month).count()
    
    # Company statistics
    total_companies = Company.objects.count()
    active_companies = Company.objects.filter(is_active=True).count()
    
    # AI Token statistics
    total_tokens_used = AIEnhancementLog.objects.aggregate(
        total=Sum('tokens_consumed')
    )['total'] or 0
    
    tokens_this_week = AIEnhancementLog.objects.filter(
        created_at__gte=last_week
    ).aggregate(total=Sum('tokens_consumed'))['total'] or 0
    
    tokens_this_month = AIEnhancementLog.objects.filter(
        created_at__gte=last_month
    ).aggregate(total=Sum('tokens_consumed'))['total'] or 0
    
    data = {
        'total_users': total_users,
        'active_users': active_users,
        'new_users_this_week': new_users_this_week,
        'new_users_this_month': new_users_this_month,
        'total_daily_reports': total_daily_reports,
        'total_weekly_reports': total_weekly_reports,
        'reports_this_week': reports_this_week,
        'reports_this_month': reports_this_month,
        'total_companies': total_companies,
        'active_companies': active_companies,
        'total_tokens_used': total_tokens_used,
        'tokens_this_week': tokens_this_week,
        'tokens_this_month': tokens_this_month,
    }
    
    serializer = DashboardStatsSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AdminPermission])
def user_management_api(request):
    """Get user management data with search and filters"""
    # Get search parameters
    search = request.GET.get('search', '')
    program_filter = request.GET.get('program', '')
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    page = int(request.GET.get('page', 1))
    
    # Build queryset
    users = User.objects.select_related('profile')
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(profile__student_id__icontains=search)
        )
    
    if program_filter:
        users = users.filter(profile__program=program_filter)
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    if date_filter:
        if date_filter == 'today':
            users = users.filter(date_joined__date=timezone.now().date())
        elif date_filter == 'week':
            users = users.filter(date_joined__gte=timezone.now().date() - timedelta(days=7))
        elif date_filter == 'month':
            users = users.filter(date_joined__gte=timezone.now().date() - timedelta(days=30))
    
    # Pagination
    paginator = Paginator(users, 50)
    page_obj = paginator.get_page(page)
    
    # Statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    new_users_today = User.objects.filter(date_joined__date=timezone.now().date()).count()
    new_users_week = User.objects.filter(date_joined__gte=timezone.now().date() - timedelta(days=7)).count()
    
    data = {
        'users': page_obj.object_list,
        'total_users': total_users,
        'active_users': active_users,
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
        'pagination': {
            'page': page_obj.number,
            'pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'total_count': paginator.count,
        }
    }
    
    serializer = UserManagementSerializer(data)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AdminPermission])
def user_actions(request):
    """Perform actions on users (ban, unban, delete, etc.)"""
    serializer = UserActionRequestSerializer(data=request.data)
    if serializer.is_valid():
        user_ids = serializer.validated_data['user_ids']
        action = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')
        
        users = User.objects.filter(id__in=user_ids)
        
        if action == 'BAN':
            users.update(is_active=False)
        elif action == 'UNBAN':
            users.update(is_active=True)
        elif action == 'DELETE':
            for user in users:
                UserAction.objects.create(
                    admin_user=request.user,
                    target_user=user,
                    action='DELETE',
                    reason=reason
                )
            users.delete()
        elif action == 'ACTIVATE':
            users.update(is_active=True)
        
        # Log the action
        for user in users:
            UserAction.objects.create(
                admin_user=request.user,
                target_user=user,
                action=action,
                reason=reason
            )
        
        return Response({
            'success': True,
            'message': f'{len(users)} users {action.lower()}ed successfully'
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AdminPermission])
def token_analytics_api(request):
    """Get token analytics data"""
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Token usage over time
    daily_usage = list(AIEnhancementLog.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('created_at__date').annotate(
        total_tokens=Sum('tokens_consumed'),
        count=Count('id')
    ).order_by('created_at__date'))
    
    # User token usage
    user_usage = list(AIEnhancementLog.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('user__username').annotate(
        total_tokens=Sum('tokens_consumed'),
        count=Count('id')
    ).order_by('-total_tokens')[:20])
    
    # Enhancement type usage
    enhancement_usage = list(AIEnhancementLog.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('enhancement_type').annotate(
        total_tokens=Sum('tokens_consumed'),
        count=Count('id')
    ).order_by('-total_tokens'))
    
    # Content type usage
    content_usage = list(AIEnhancementLog.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('content_type').annotate(
        total_tokens=Sum('tokens_consumed'),
        count=Count('id')
    ).order_by('-total_tokens'))
    
    # Total statistics
    total_tokens = AIEnhancementLog.objects.aggregate(
        total=Sum('tokens_consumed')
    )['total'] or 0
    
    period_tokens = AIEnhancementLog.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).aggregate(total=Sum('tokens_consumed'))['total'] or 0
    
    total_enhancements = AIEnhancementLog.objects.count()
    period_enhancements = AIEnhancementLog.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).count()
    
    data = {
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
        'daily_usage': daily_usage,
        'user_usage': user_usage,
        'enhancement_usage': enhancement_usage,
        'content_usage': content_usage,
        'total_tokens': total_tokens,
        'period_tokens': period_tokens,
        'total_enhancements': total_enhancements,
        'period_enhancements': period_enhancements,
    }
    
    serializer = TokenAnalyticsSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AdminPermission])
def report_analytics_api(request):
    """Get report analytics data"""
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Daily report statistics
    daily_reports_stats = list(DailyReport.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('created_at__date').annotate(
        count=Count('id'),
        total_hours=Sum('hours_spent')
    ).order_by('created_at__date'))
    
    # Weekly report statistics
    weekly_reports_stats = list(WeeklyReport.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('created_at__date').annotate(
        count=Count('id'),
        total_hours=Sum('total_hours')
    ).order_by('created_at__date'))
    
    # User report activity
    user_report_activity = list(DailyReport.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('student__username').annotate(
        report_count=Count('id'),
        total_hours=Sum('hours_spent')
    ).order_by('-report_count')[:20])
    
    # Completion rates
    total_weekly_reports = WeeklyReport.objects.count()
    completed_weekly_reports = WeeklyReport.objects.filter(is_complete=True).count()
    completion_rate = (completed_weekly_reports / total_weekly_reports * 100) if total_weekly_reports > 0 else 0
    
    # Program-wise statistics
    program_stats = list(DailyReport.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('student__profile__program').annotate(
        report_count=Count('id'),
        total_hours=Sum('hours_spent')
    ).order_by('-report_count'))
    
    data = {
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
        'daily_reports_stats': daily_reports_stats,
        'weekly_reports_stats': weekly_reports_stats,
        'user_report_activity': user_report_activity,
        'total_weekly_reports': total_weekly_reports,
        'completed_weekly_reports': completed_weekly_reports,
        'completion_rate': completion_rate,
        'program_stats': program_stats,
    }
    
    serializer = ReportAnalyticsSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AdminPermission])
def recent_activity(request):
    """Get recent activity data"""
    # Recent activities
    recent_users = User.objects.order_by('-date_joined')[:10]
    recent_reports = list(DailyReport.objects.select_related('student').order_by('-created_at')[:10].values(
        'student__username', 'student__first_name', 'student__last_name', 'date', 'hours_spent', 'created_at'
    ))
    recent_ai_logs = list(AIEnhancementLog.objects.select_related('user').order_by('-created_at')[:10].values(
        'user__username', 'user__first_name', 'user__last_name', 'enhancement_type', 'content_type', 
        'tokens_consumed', 'created_at'
    ))
    
    # User actions
    recent_actions = UserAction.objects.select_related('admin_user', 'target_user').order_by('-created_at')[:10]
    
    # Program distribution
    program_stats = list(UserProfile.objects.values('program').annotate(
        count=Count('id')
    ).order_by('-count'))
    
    # Industry distribution
    industry_stats = list(Company.objects.values('industry_type').annotate(
        count=Count('id')
    ).order_by('-count'))
    
    data = {
        'recent_users': recent_users,
        'recent_reports': recent_reports,
        'recent_ai_logs': recent_ai_logs,
        'recent_actions': recent_actions,
        'program_stats': program_stats,
        'industry_stats': industry_stats,
    }
    
    serializer = RecentActivitySerializer(data)
    return Response(serializer.data)


class TokenUsageViewSet(viewsets.ModelViewSet):
    """ViewSet for token usage data"""
    queryset = TokenUsage.objects.all()
    serializer_class = TokenUsageSerializer
    permission_classes = [AdminPermission]
    filterset_fields = ['enhancement_type', 'content_type', 'created_at']
    search_fields = ['user__username', 'user__email']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get token usage statistics"""
        total_tokens = TokenUsage.objects.aggregate(total=Sum('tokens_consumed'))['total'] or 0
        total_cost = TokenUsage.objects.aggregate(total=Sum('cost_estimate'))['total'] or 0
        
        # Average tokens per user
        user_count = TokenUsage.objects.values('user').distinct().count()
        average_tokens_per_user = total_tokens / user_count if user_count > 0 else 0
        
        # Top users
        top_users = list(TokenUsage.objects.values('user__username').annotate(
            total_tokens=Sum('tokens_consumed')
        ).order_by('-total_tokens')[:10])
        
        # Enhancement type breakdown
        enhancement_type_breakdown = list(TokenUsage.objects.values('enhancement_type').annotate(
            total_tokens=Sum('tokens_consumed'),
            count=Count('id')
        ).order_by('-total_tokens'))
        
        # Content type breakdown
        content_type_breakdown = list(TokenUsage.objects.values('content_type').annotate(
            total_tokens=Sum('tokens_consumed'),
            count=Count('id')
        ).order_by('-total_tokens'))
        
        # Daily usage trend
        daily_usage_trend = list(TokenUsage.objects.values('created_at__date').annotate(
            total_tokens=Sum('tokens_consumed')
        ).order_by('created_at__date')[:30])
        
        data = {
            'total_tokens': total_tokens,
            'total_cost': total_cost,
            'average_tokens_per_user': average_tokens_per_user,
            'top_users': top_users,
            'enhancement_type_breakdown': enhancement_type_breakdown,
            'content_type_breakdown': content_type_breakdown,
            'daily_usage_trend': daily_usage_trend,
        }
        
        serializer = TokenUsageStatsSerializer(data)
        return Response(serializer.data)


class UserActionViewSet(viewsets.ModelViewSet):
    """ViewSet for user actions"""
    queryset = UserAction.objects.all()
    serializer_class = UserActionSerializer
    permission_classes = [AdminPermission]
    filterset_fields = ['action', 'created_at']
    search_fields = ['admin_user__username', 'target_user__username', 'reason']
    ordering = ['-created_at']


class SystemMetricsViewSet(viewsets.ModelViewSet):
    """ViewSet for system metrics"""
    queryset = SystemMetrics.objects.all()
    serializer_class = SystemMetricsSerializer
    permission_classes = [AdminPermission]
    ordering = ['-date'] 