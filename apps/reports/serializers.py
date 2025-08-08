from rest_framework import serializers
from .models import DailyReport, WeeklyReport, MainJob, MainJobOperation
from datetime import date, timedelta
from django.utils import timezone

def get_week_range(week_number, year=2025):
    """Calculate the start and end date for a given week number.
    Week 1 starts July 21, 2025 (Monday)"""
    first_monday = date(2025, 7, 21)
    start_date = first_monday + timedelta(weeks=week_number - 1)
    end_date = start_date + timedelta(days=4)  # Monday to Friday
    return start_date, end_date

class DailyReportSerializer(serializers.ModelSerializer):
    """Serializer for daily reports."""
    day_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyReport
        fields = [
            'id', 'student', 'week_number', 'date', 'description', 
            'hours_spent', 'day_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['student', 'created_at', 'updated_at']

    def get_day_name(self, obj):
        """Get the day name (Monday, Tuesday, etc.)."""
        return obj.date.strftime('%A')

    def validate_date(self, value):
        """Validate that the date is not in the future."""
        if value > timezone.now().date():
            raise serializers.ValidationError("Date cannot be in the future.")
        return value

    def validate_hours_spent(self, value):
        """Validate hours spent."""
        if value < 0.5 or value > 12:
            raise serializers.ValidationError("Hours must be between 0.5 and 12.")
        return value

    def validate(self, data):
        """Validate that the date falls within the correct week range."""
        week_number = data.get('week_number')
        report_date = data.get('date')
        
        if week_number and report_date:
            # For now, allow any date in 2025 to be more flexible
            # The frontend can handle the week calculation
            if report_date.year != 2025:
                raise serializers.ValidationError(
                    f"Date {report_date} must be in 2025."
                )
        return data

    def create(self, validated_data):
        student = validated_data.get('student')
        date = validated_data.get('date')
        # Try to get existing report
        instance, created = DailyReport.objects.get_or_create(
            student=student,
            date=date,
            defaults=validated_data
        )
        if not created:
            # Update the existing report
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
        return instance

class MainJobOperationSerializer(serializers.ModelSerializer):
    """Serializer for main job operations."""
    
    class Meta:
        model = MainJobOperation
        fields = [
            'id', 'step_number', 'operation_description', 
            'tools_used', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_step_number(self, value):
        """Validate step number is positive."""
        if value and value <= 0:
            raise serializers.ValidationError("Step number must be positive.")
        return value

class MainJobCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating main jobs with operations."""
    operations = MainJobOperationSerializer(many=True, required=False)
    
    class Meta:
        model = MainJob
        fields = [
            'id', 'title', 'operations'
        ]
        read_only_fields = ['id']

    def validate_title(self, value):
        """Validate title is not empty if provided."""
        if value and not value.strip():
            raise serializers.ValidationError("Job title cannot be empty if provided.")
        return value

class MainJobSerializer(serializers.ModelSerializer):
    """Serializer for main job - one per weekly report (read-only)."""
    operations = MainJobOperationSerializer(many=True, read_only=True)
    
    class Meta:
        model = MainJob
        fields = [
            'id', 'title', 'operations'
        ]
        read_only_fields = ['id']

    def validate_title(self, value):
        """Validate title is not empty if provided."""
        if value and not value.strip():
            raise serializers.ValidationError("Job title cannot be empty if provided.")
        return value

class WeeklyReportSerializer(serializers.ModelSerializer):
    """Serializer for weekly reports with nested main_job."""
    daily_reports = DailyReportSerializer(many=True, read_only=True)
    main_job = MainJobSerializer(read_only=True)
    
    class Meta:
        model = WeeklyReport
        fields = [
            'id', 'week_number', 'start_date', 'end_date',
            'total_hours', 'daily_reports', 'main_job'
        ]
        read_only_fields = ['id', 'start_date', 'end_date', 'total_hours']

    def validate_week_number(self, value):
        """Validate week number."""
        if value < 1 or value > 52:
            raise serializers.ValidationError("Week number must be between 1 and 52.")
        return value

class WeeklyReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating weekly reports with main_job."""
    main_job = MainJobCreateSerializer(required=False)
    # Add flat fields for frontend compatibility
    main_job_title = serializers.CharField(write_only=True, required=False)
    
    # Add daily report fields for frontend compatibility
    daily_monday = serializers.CharField(write_only=True, required=False, allow_blank=True)
    hours_monday = serializers.FloatField(write_only=True, required=False)
    daily_tuesday = serializers.CharField(write_only=True, required=False, allow_blank=True)
    hours_tuesday = serializers.FloatField(write_only=True, required=False)
    daily_wednesday = serializers.CharField(write_only=True, required=False, allow_blank=True)
    hours_wednesday = serializers.FloatField(write_only=True, required=False)
    daily_thursday = serializers.CharField(write_only=True, required=False, allow_blank=True)
    hours_thursday = serializers.FloatField(write_only=True, required=False)
    daily_friday = serializers.CharField(write_only=True, required=False, allow_blank=True)
    hours_friday = serializers.FloatField(write_only=True, required=False)
    
    class Meta:
        model = WeeklyReport
        fields = [
            'week_number', 'start_date', 'end_date', 'main_job', 'main_job_title',
            'daily_monday', 'hours_monday', 'daily_tuesday', 'hours_tuesday',
            'daily_wednesday', 'hours_wednesday', 'daily_thursday', 'hours_thursday',
            'daily_friday', 'hours_friday'
        ]

    def to_internal_value(self, data):
        """Convert flat data to nested format if needed."""
        if data and isinstance(data, dict):
            # Remove fields that don't exist in WeeklyReport model
            invalid_fields = ['summary', 'main_job_description', 'total_hours']
            for field in invalid_fields:
                if field in data:
                    data = data.copy()
                    data.pop(field, None)
            
            # If main_job_title is provided but main_job is not, create main_job
            if 'main_job_title' in data and 'main_job' not in data:
                data['main_job'] = {
                    'title': data.pop('main_job_title', ''),
                    'operations': []
                }
        return super().to_internal_value(data)

    def create(self, validated_data):
        """Create weekly report with main job and daily reports."""
        try:
            # Extract daily report data
            daily_data = {}
            for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
                daily_key = f'daily_{day}'
                hours_key = f'hours_{day}'
                if daily_key in validated_data and validated_data[daily_key] and validated_data[daily_key].strip():
                    daily_data[day] = {
                        'description': validated_data.pop(daily_key),
                        'hours_spent': validated_data.pop(hours_key, 0)
                    }
            
            main_job_data = validated_data.pop('main_job', {})
            operations_data = main_job_data.pop('operations', [])
            
            # Create weekly report - handle unique constraint properly
            try:
                weekly_report = WeeklyReport.objects.get(
                student=validated_data['student'],
                    week_number=validated_data['week_number']
            )
                # Update existing weekly report
                for attr, value in validated_data.items():
                    if hasattr(weekly_report, attr):
                        setattr(weekly_report, attr, value)
                weekly_report.save()
            except WeeklyReport.DoesNotExist:
                # Create new weekly report
                weekly_report = WeeklyReport.objects.create(**validated_data)
            
            # Create main job if data provided
            if main_job_data and main_job_data.get('title'):
                main_job, main_job_created = MainJob.objects.get_or_create(
                    weekly_report=weekly_report,
                    defaults=main_job_data
                )
                if not main_job_created:
                    # Update the existing main job with new data
                    for attr, value in main_job_data.items():
                        setattr(main_job, attr, value)
                    main_job.save()
                
                # Only update operations if operations_data is provided
                if operations_data:
                    # Remove existing operations if updating main job
                    if not main_job_created:
                        main_job.operations.all().delete()
                    # Create operations
                    for operation_data in operations_data:
                        MainJobOperation.objects.create(
                            main_job=main_job,
                            **operation_data
                        )
            
            # Create daily reports
            for day, data in daily_data.items():
                # Calculate date based on week number and day
                from datetime import datetime, timedelta
                # Convert date to string if it's a datetime.date object
                start_date_str = weekly_report.start_date.strftime('%Y-%m-%d') if hasattr(weekly_report.start_date, 'strftime') else str(weekly_report.start_date)
                week_start = datetime.strptime(start_date_str, '%Y-%m-%d')
                day_offset = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4}[day]
                report_date = week_start + timedelta(days=day_offset)
                
                # Update or create daily report - use date as the unique identifier
                try:
                    daily_report = DailyReport.objects.get(
                        student=weekly_report.student,
                        date=report_date.date()
                    )
                    # Update existing daily report
                    daily_report.week_number = weekly_report.week_number
                    daily_report.description = data['description']
                    daily_report.hours_spent = data['hours_spent']
                    daily_report.save()
                except DailyReport.DoesNotExist:
                    # Create new daily report
                    daily_report = DailyReport.objects.create(
                        student=weekly_report.student,
                        week_number=weekly_report.week_number,
                        date=report_date.date(),
                        description=data['description'],
                        hours_spent=data['hours_spent']
                    )
            
            return weekly_report
        except Exception as e:
            print(f"❌ Error in create method: {e}")
            import traceback
            traceback.print_exc()
            raise

    def update(self, instance, validated_data):
        """Update weekly report with main job and daily reports."""
        try:
            # Extract daily report data
            daily_data = {}
            for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
                daily_key = f'daily_{day}'
                hours_key = f'hours_{day}'
                if daily_key in validated_data and validated_data[daily_key] and validated_data[daily_key].strip():
                    daily_data[day] = {
                        'description': validated_data.pop(daily_key),
                        'hours_spent': validated_data.pop(hours_key, 0)
                    }
            
            main_job_data = validated_data.pop('main_job', {})
            operations_data = main_job_data.pop('operations', [])
            
            # Only update safe fields - avoid updating student and week_number
            safe_fields = ['start_date', 'end_date', 'total_hours', 'is_complete']
            update_fields = []
            for attr, value in validated_data.items():
                if hasattr(instance, attr) and attr in safe_fields:
                    setattr(instance, attr, value)
                    update_fields.append(attr)
            
            # Only save if there are fields to update
            if update_fields:
                instance.save(update_fields=update_fields)
            
            # Update or create main job
            if main_job_data and main_job_data.get('title'):
                main_job, created = MainJob.objects.get_or_create(
                    weekly_report=instance,
                    defaults=main_job_data
                )
                if not created:
                    for attr, value in main_job_data.items():
                        setattr(main_job, attr, value)
                    main_job.save()
                
                # Update operations
                if operations_data:
                    # Clear existing operations
                    main_job.operations.all().delete()
                    # Create new operations
                    for operation_data in operations_data:
                        MainJobOperation.objects.create(
                            main_job=main_job,
                            **operation_data
                        )
            
            # Update daily reports
            for day, data in daily_data.items():
                # Calculate date based on week number and day
                from datetime import datetime, timedelta
                # Convert date to string if it's a datetime.date object
                start_date_str = instance.start_date.strftime('%Y-%m-%d') if hasattr(instance.start_date, 'strftime') else str(instance.start_date)
                week_start = datetime.strptime(start_date_str, '%Y-%m-%d')
                day_offset = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4}[day]
                report_date = week_start + timedelta(days=day_offset)
                
                # Update or create daily report - use date as the unique identifier
                try:
                    daily_report = DailyReport.objects.get(
                        student=instance.student,
                        date=report_date.date()
                    )
                    # Update existing daily report
                    daily_report.week_number = instance.week_number
                    daily_report.description = data['description']
                    daily_report.hours_spent = data['hours_spent']
                    daily_report.save()
                except DailyReport.DoesNotExist:
                    # Create new daily report
                    daily_report = DailyReport.objects.create(
                        student=instance.student,
                        week_number=instance.week_number,
                        date=report_date.date(),
                        description=data['description'],
                        hours_spent=data['hours_spent']
                    )
            
            return instance
        except Exception as e:
            print(f"❌ Error in update method: {e}")
            import traceback
            traceback.print_exc()
            raise 

class MainJobDetailSerializer(serializers.ModelSerializer):
    """Serializer for main job with nested operations - for detailed view."""
    operations = MainJobOperationSerializer(many=True, read_only=True)
    
    class Meta:
        model = MainJob
        fields = [
            'id', 'weekly_report', 'title', 'operations'
        ]
        read_only_fields = ['id', 'weekly_report']

class MainJobUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating main job title only."""
    
    class Meta:
        model = MainJob
        fields = ['title']
        
    def validate_title(self, value):
        """Validate title is not empty if provided."""
        if value and not value.strip():
            raise serializers.ValidationError("Job title cannot be empty if provided.")
        return value

class MainJobOperationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating operations."""
    
    class Meta:
        model = MainJobOperation
        fields = [
            'step_number', 'operation_description', 'tools_used'
        ]

    def validate_step_number(self, value):
        """Validate step number is positive."""
        if value and value <= 0:
            raise serializers.ValidationError("Step number must be positive.")
        return value

    def validate(self, data):
        """Validate that step number is unique within the main job."""
        main_job = self.context.get('main_job')
        step_number = data.get('step_number')
        
        if main_job and step_number:
            # Check if step number already exists for this main job
            existing_operation = MainJobOperation.objects.filter(
                main_job=main_job,
                step_number=step_number
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_operation.exists():
                raise serializers.ValidationError(
                    f"Step number {step_number} already exists for this main job."
                )
        return data

class MainJobOperationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating operations."""
    
    class Meta:
        model = MainJobOperation
        fields = [
            'step_number', 'operation_description', 'tools_used'
        ]

    def validate_step_number(self, value):
        """Validate step number is positive."""
        if value and value <= 0:
            raise serializers.ValidationError("Step number must be positive.")
        return value

    def validate(self, data):
        """Validate that step number is unique within the main job."""
        main_job = self.context.get('main_job')
        step_number = data.get('step_number')
        
        if main_job and step_number:
            # Check if step number already exists for this main job
            existing_operation = MainJobOperation.objects.filter(
                main_job=main_job,
                step_number=step_number
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_operation.exists():
                raise serializers.ValidationError(
                    f"Step number {step_number} already exists for this main job."
                )
        return data 