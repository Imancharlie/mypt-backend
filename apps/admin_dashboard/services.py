from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import TokenUsage, SystemMetrics
from apps.reports.models import AIEnhancementLog, DailyReport, WeeklyReport
from apps.companies.models import Company
from django.contrib.auth.models import User


class TokenTrackingService:
    """Service for tracking AI token usage"""
    
    @staticmethod
    def log_token_usage(user, tokens_consumed, enhancement_type=None, content_type=None, cost_estimate=0):
        """Log token usage for analytics"""
        TokenUsage.objects.create(
            user=user,
            tokens_consumed=tokens_consumed,
            enhancement_type=enhancement_type,
            content_type=content_type,
            cost_estimate=cost_estimate
        )
    
    @staticmethod
    def get_user_token_stats(user):
        """Get token statistics for a specific user"""
        total_tokens = TokenUsage.objects.filter(user=user).aggregate(
            total=Sum('tokens_consumed')
        )['total'] or 0
        
        total_cost = TokenUsage.objects.filter(user=user).aggregate(
            total=Sum('cost_estimate')
        )['total'] or 0
        
        usage_by_type = TokenUsage.objects.filter(user=user).values('enhancement_type').annotate(
            total_tokens=Sum('tokens_consumed'),
            count=Count('id')
        ).order_by('-total_tokens')
        
        return {
            'total_tokens': total_tokens,
            'total_cost': total_cost,
            'usage_by_type': list(usage_by_type)
        }
    
    @staticmethod
    def get_system_token_stats():
        """Get system-wide token statistics"""
        total_tokens = TokenUsage.objects.aggregate(
            total=Sum('tokens_consumed')
        )['total'] or 0
        
        total_cost = TokenUsage.objects.aggregate(
            total=Sum('cost_estimate')
        )['total'] or 0
        
        # Top users by token usage
        top_users = TokenUsage.objects.values('user__username').annotate(
            total_tokens=Sum('tokens_consumed')
        ).order_by('-total_tokens')[:10]
        
        # Usage by enhancement type
        enhancement_breakdown = TokenUsage.objects.values('enhancement_type').annotate(
            total_tokens=Sum('tokens_consumed'),
            count=Count('id')
        ).order_by('-total_tokens')
        
        return {
            'total_tokens': total_tokens,
            'total_cost': total_cost,
            'top_users': list(top_users),
            'enhancement_breakdown': list(enhancement_breakdown)
        }


class SystemMetricsService:
    """Service for tracking system-wide metrics"""
    
    @staticmethod
    def update_daily_metrics():
        """Update daily system metrics"""
        today = timezone.now().date()
        
        # Get current metrics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        total_reports = DailyReport.objects.count()
        total_companies = Company.objects.count()
        
        # Get token usage from AI logs
        total_tokens_used = AIEnhancementLog.objects.aggregate(
            total=Sum('tokens_consumed')
        )['total'] or 0
        
        # Estimate cost (rough calculation)
        total_cost = total_tokens_used * 0.00002  # Approximate cost per token
        
        # Create or update metrics for today
        metrics, created = SystemMetrics.objects.get_or_create(
            date=today,
            defaults={
                'total_users': total_users,
                'active_users': active_users,
                'total_reports': total_reports,
                'total_companies': total_companies,
                'total_tokens_used': total_tokens_used,
                'total_cost': total_cost
            }
        )
        
        if not created:
            # Update existing metrics
            metrics.total_users = total_users
            metrics.active_users = active_users
            metrics.total_reports = total_reports
            metrics.total_companies = total_companies
            metrics.total_tokens_used = total_tokens_used
            metrics.total_cost = total_cost
            metrics.save()
        
        return metrics
    
    @staticmethod
    def get_metrics_trend(days=30):
        """Get metrics trend over specified days"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        metrics = SystemMetrics.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date')
        
        return list(metrics.values('date', 'total_users', 'active_users', 
                                 'total_reports', 'total_companies', 
                                 'total_tokens_used', 'total_cost'))
    
    @staticmethod
    def get_current_metrics():
        """Get current system metrics"""
        today = timezone.now().date()
        
        # Try to get today's metrics
        try:
            metrics = SystemMetrics.objects.get(date=today)
            return {
                'total_users': metrics.total_users,
                'active_users': metrics.active_users,
                'total_reports': metrics.total_reports,
                'total_companies': metrics.total_companies,
                'total_tokens_used': metrics.total_tokens_used,
                'total_cost': metrics.total_cost,
                'date': metrics.date
            }
        except SystemMetrics.DoesNotExist:
            # Calculate current metrics
            return SystemMetricsService.update_daily_metrics()


class UserAnalyticsService:
    """Service for user analytics"""
    
    @staticmethod
    def get_user_registration_trend(days=30):
        """Get user registration trend"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        daily_registrations = User.objects.filter(
            date_joined__date__range=[start_date, end_date]
        ).values('date_joined__date').annotate(
            count=Count('id')
        ).order_by('date_joined__date')
        
        return list(daily_registrations)
    
    @staticmethod
    def get_program_distribution():
        """Get user distribution by program"""
        from apps.users.models import UserProfile
        
        program_stats = UserProfile.objects.values('program').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return list(program_stats)
    
    @staticmethod
    def get_user_activity_stats():
        """Get user activity statistics"""
        # Users who logged in recently
        recent_logins = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Users who created reports recently
        active_reporters = DailyReport.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).values('student').distinct().count()
        
        # New users this week
        new_users_week = User.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        return {
            'recent_logins': recent_logins,
            'active_reporters': active_reporters,
            'new_users_week': new_users_week
        }


class ReportAnalyticsService:
    """Service for report analytics"""
    
    @staticmethod
    def get_report_creation_trend(days=30):
        """Get report creation trend"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        daily_reports = DailyReport.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).values('created_at__date').annotate(
            count=Count('id'),
            total_hours=Sum('hours_spent')
        ).order_by('created_at__date')
        
        return list(daily_reports)
    
    @staticmethod
    def get_completion_rates():
        """Get report completion rates"""
        total_weekly_reports = WeeklyReport.objects.count()
        completed_weekly_reports = WeeklyReport.objects.filter(is_complete=True).count()
        
        completion_rate = (completed_weekly_reports / total_weekly_reports * 100) if total_weekly_reports > 0 else 0
        
        return {
            'total_weekly_reports': total_weekly_reports,
            'completed_weekly_reports': completed_weekly_reports,
            'completion_rate': completion_rate
        }
    
    @staticmethod
    def get_top_reporters(limit=10):
        """Get top users by report count"""
        top_reporters = DailyReport.objects.values('student__username').annotate(
            report_count=Count('id'),
            total_hours=Sum('hours_spent')
        ).order_by('-report_count')[:limit]
        
        return list(top_reporters) 