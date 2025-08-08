from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class TokenUsage(models.Model):
    """Track AI token usage for analytics"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='token_usage')
    tokens_consumed = models.IntegerField(default=0)
    enhancement_type = models.CharField(max_length=50, blank=True, null=True)
    content_type = models.CharField(max_length=50, blank=True, null=True)
    cost_estimate = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Token Usage'
        verbose_name_plural = 'Token Usage'
    
    def __str__(self):
        return f"{self.user.username} - {self.tokens_consumed} tokens - {self.created_at.date()}"


class UserAction(models.Model):
    """Track admin actions on users"""
    ACTION_CHOICES = [
        ('BAN', 'Banned'),
        ('UNBAN', 'Unbanned'),
        ('DELETE', 'Deleted'),
        ('RESTORE', 'Restored'),
        ('SUSPEND', 'Suspended'),
        ('ACTIVATE', 'Activated'),
    ]
    
    admin_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_actions')
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_actions')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Action'
        verbose_name_plural = 'User Actions'
    
    def __str__(self):
        return f"{self.admin_user.username} {self.action} {self.target_user.username}"


class SystemMetrics(models.Model):
    """Track system-wide metrics"""
    total_users = models.IntegerField(default=0)
    total_reports = models.IntegerField(default=0)
    total_companies = models.IntegerField(default=0)
    total_tokens_used = models.IntegerField(default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date = models.DateField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'System Metric'
        verbose_name_plural = 'System Metrics'
    
    def __str__(self):
        return f"Metrics for {self.date} - {self.total_users} users, {self.total_reports} reports" 