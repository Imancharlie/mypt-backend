from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from apps.reports.models import DailyReport, WeeklyReport, AIEnhancementLog
from apps.companies.models import Company
from apps.users.models import UserProfile
from .models import TokenUsage, UserAction, SystemMetrics


@staff_member_required
def admin_dashboard(request):
    """Main admin dashboard with analytics"""
    
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
    
    # Recent activities
    recent_users = User.objects.order_by('-date_joined')[:10]
    recent_reports = DailyReport.objects.select_related('student').order_by('-created_at')[:10]
    recent_ai_logs = AIEnhancementLog.objects.select_related('user').order_by('-created_at')[:10]
    
    # User actions
    recent_actions = UserAction.objects.select_related('admin_user', 'target_user').order_by('-created_at')[:10]
    
    # Program distribution
    program_stats = UserProfile.objects.values('program').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Industry distribution
    industry_stats = Company.objects.values('industry_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
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
        'recent_users': recent_users,
        'recent_reports': recent_reports,
        'recent_ai_logs': recent_ai_logs,
        'recent_actions': recent_actions,
        'program_stats': program_stats,
        'industry_stats': industry_stats,
    }
    
    return render(request, 'admin_dashboard/dashboard.html', context)


@staff_member_required
def user_management(request):
    """Enhanced user management view"""
    
    # Get search parameters
    search = request.GET.get('search', '')
    program_filter = request.GET.get('program', '')
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    
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
    from django.core.paginator import Paginator
    paginator = Paginator(users, 50)  # 50 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    new_users_today = User.objects.filter(date_joined__date=timezone.now().date()).count()
    new_users_week = User.objects.filter(date_joined__gte=timezone.now().date() - timedelta(days=7)).count()
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'program_filter': program_filter,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'total_users': total_users,
        'active_users': active_users,
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
        'program_choices': UserProfile.PROGRAM_CHOICES,
    }
    
    return render(request, 'admin_dashboard/user_management.html', context)


@staff_member_required
def token_analytics(request):
    """AI token usage analytics"""
    
    # Get date range
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Token usage over time
    daily_usage = AIEnhancementLog.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('created_at__date').annotate(
        total_tokens=Sum('tokens_consumed'),
        count=Count('id')
    ).order_by('created_at__date')
    
    # User token usage
    user_usage = AIEnhancementLog.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('user__username').annotate(
        total_tokens=Sum('tokens_consumed'),
        count=Count('id')
    ).order_by('-total_tokens')[:20]
    
    # Enhancement type usage
    enhancement_usage = AIEnhancementLog.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('enhancement_type').annotate(
        total_tokens=Sum('tokens_consumed'),
        count=Count('id')
    ).order_by('-total_tokens')
    
    # Content type usage
    content_usage = AIEnhancementLog.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('content_type').annotate(
        total_tokens=Sum('tokens_consumed'),
        count=Count('id')
    ).order_by('-total_tokens')
    
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
    
    context = {
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
    
    return render(request, 'admin_dashboard/token_analytics.html', context)


@staff_member_required
def report_analytics(request):
    """Report creation and completion analytics"""
    
    # Get date range
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Daily report statistics
    daily_reports_stats = DailyReport.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('created_at__date').annotate(
        count=Count('id'),
        total_hours=Sum('hours_spent')
    ).order_by('created_at__date')
    
    # Weekly report statistics
    weekly_reports_stats = WeeklyReport.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('created_at__date').annotate(
        count=Count('id'),
        total_hours=Sum('total_hours')
    ).order_by('created_at__date')
    
    # User report activity
    user_report_activity = DailyReport.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('student__username').annotate(
        report_count=Count('id'),
        total_hours=Sum('hours_spent')
    ).order_by('-report_count')[:20]
    
    # Completion rates
    total_weekly_reports = WeeklyReport.objects.count()
    completed_weekly_reports = WeeklyReport.objects.filter(is_complete=True).count()
    completion_rate = (completed_weekly_reports / total_weekly_reports * 100) if total_weekly_reports > 0 else 0
    
    # Program-wise statistics
    program_stats = DailyReport.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('student__profile__program').annotate(
        report_count=Count('id'),
        total_hours=Sum('hours_spent')
    ).order_by('-report_count')
    
    context = {
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
    
    return render(request, 'admin_dashboard/report_analytics.html', context) 