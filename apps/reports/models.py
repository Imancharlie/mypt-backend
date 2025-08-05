from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import datetime, timedelta
import calendar

class DailyReport(models.Model):
    """Simplified daily report with only essential fields."""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_reports')
    week_number = models.IntegerField(help_text="Week number for linking to weekly report")
    date = models.DateField()
    description = models.TextField(help_text="Description of work done")
    hours_spent = models.DecimalField(
        max_digits=4, 
        decimal_places=1,
        validators=[MinValueValidator(0.5), MaxValueValidator(12)],
        help_text="Hours spent (0.5 to 12 hours)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'date']
        ordering = ['date']

    def __str__(self):
        return f"{self.student.username} - {self.date} ({self.hours_spent}h)"

class MainJob(models.Model):
    """Main job for a weekly report - one per week."""
    weekly_report = models.OneToOneField('WeeklyReport', on_delete=models.CASCADE, related_name='main_job', null=True, blank=True)
    title = models.CharField(max_length=200, help_text="Title of the main job for this week", null=True, blank=True)
    description = models.TextField(help_text="Description of the main job", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.title or 'Untitled'} - Week {self.weekly_report.week_number if self.weekly_report else 'Unknown'}"

class MainJobOperation(models.Model):
    """Operations/steps for the main job of a week."""
    main_job = models.ForeignKey(MainJob, on_delete=models.CASCADE, related_name='operations', null=True, blank=True)
    step_number = models.IntegerField(help_text="Step number in the operation sequence", null=True, blank=True)
    operation_description = models.TextField(help_text="Description of this operation step", null=True, blank=True)
    tools_used = models.TextField(help_text="Tools, machinery, equipment used for this step", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['step_number']
        unique_together = ['main_job', 'step_number']

    def __str__(self):
        return f"Step {self.step_number or 'Unknown'}: {self.operation_description[:50] if self.operation_description else 'No description'}..."

class WeeklyReport(models.Model):
    """Weekly report auto-generated from daily reports."""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weekly_reports')
    week_number = models.IntegerField(help_text="Week number for linking to weekly report")
    start_date = models.DateField(help_text="Start date (Monday)")
    end_date = models.DateField(help_text="End date (Friday)")
    total_hours = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    is_complete = models.BooleanField(default=False, help_text="True if all 5 days have reports")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'week_number']
        ordering = ['-week_number']

    def __str__(self):
        return f"Week {self.week_number} - {self.student.username} ({'Complete' if self.is_complete else 'Incomplete'})"

    def get_daily_reports(self):
        """Get all daily reports for this week."""
        return DailyReport.objects.filter(
            student=self.student,
            week_number=self.week_number
        ).order_by('date')

    def update_completion_status(self):
        """Update completion status based on daily reports."""
        daily_count = self.get_daily_reports().count()
        self.is_complete = daily_count >= 5  # Monday to Friday
        self.save()

    def calculate_total_hours(self):
        """Calculate total hours from daily reports."""
        daily_reports = self.get_daily_reports()
        total = sum(report.hours_spent for report in daily_reports)
        self.total_hours = total
        self.save()
        return total

    @classmethod
    def create_from_daily_reports(cls, student, week_number):
        """Create or update weekly report from daily reports."""
        # Get all daily reports for this week
        daily_reports = DailyReport.objects.filter(
            student=student,
            week_number=week_number
        ).order_by('date')

        if not daily_reports.exists():
            return None

        # Calculate start and end dates
        start_date = daily_reports.first().date
        end_date = daily_reports.last().date

        # Create or get weekly report
        weekly_report, created = cls.objects.get_or_create(
            student=student,
            week_number=week_number,
            defaults={
                'start_date': start_date,
                'end_date': end_date,
                'total_hours': 0,
                'is_complete': False
            }
        )

        # Update completion status and total hours
        weekly_report.update_completion_status()
        weekly_report.calculate_total_hours()

        return weekly_report

# Legacy models with null/blank fields to prevent migration issues
class GeneralReport(models.Model):
    """Legacy model - kept for migration compatibility."""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='legacy_general_reports', null=True, blank=True)
    title = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', null=True, blank=True)
    introduction = models.TextField(null=True, blank=True)
    company_overview = models.TextField(null=True, blank=True)
    training_objectives = models.TextField(null=True, blank=True)
    methodology = models.TextField(null=True, blank=True)
    achievements = models.TextField(null=True, blank=True)
    challenges_faced = models.TextField(null=True, blank=True)
    skills_acquired = models.TextField(null=True, blank=True)
    recommendations = models.TextField(null=True, blank=True)
    conclusion = models.TextField(null=True, blank=True)
    acknowledgments = models.TextField(null=True, blank=True)
    compiled_from = models.ManyToManyField(WeeklyReport, blank=True, related_name='legacy_compiled_reports')
    is_ai_enhanced = models.BooleanField(default=False, null=True, blank=True)
    word_count = models.IntegerField(default=0, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Legacy General Report - {self.user.username if self.user else 'No User'}"

class AIEnhancementLog(models.Model):
    """Legacy model - kept for migration compatibility."""
    CONTENT_TYPE_CHOICES = [
        ('DAILY', 'Daily Report'),
        ('WEEKLY', 'Weekly Report'),
        ('GENERAL', 'General Report'),
    ]
    
    ENHANCEMENT_TYPE_CHOICES = [
        ('ENHANCE', 'Text Enhancement'),
        ('SUGGEST', 'Improvement Suggestions'),
        ('GENERATE', 'Content Generation'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='legacy_ai_logs', null=True, blank=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, null=True, blank=True)
    enhancement_type = models.CharField(max_length=20, choices=ENHANCEMENT_TYPE_CHOICES, null=True, blank=True)
    original_content = models.TextField(null=True, blank=True)
    enhanced_content = models.TextField(null=True, blank=True)
    tokens_consumed = models.IntegerField(default=0, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Legacy AI Log - {self.user.username if self.user else 'No User'} - {self.enhancement_type or 'No Type'}"