from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as filters
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from .models import DailyReport, WeeklyReport, MainJob, MainJobOperation
from .serializers import (
    DailyReportSerializer, WeeklyReportSerializer, WeeklyReportCreateSerializer,
    MainJobSerializer, MainJobOperationSerializer, MainJobDetailSerializer,
    MainJobUpdateSerializer, MainJobOperationCreateSerializer, MainJobOperationUpdateSerializer
)
from apps.exporter.services import export_weekly_report_pdf, export_weekly_report_docx
import anthropic
import json
import os
from django.conf import settings

# Configure Anthropic Claude
anthropic_client = anthropic.Anthropic(
    api_key=os.getenv('ANTHROPIC_API_KEY', 'your-api-key-here')
)

class DailyReportViewSet(viewsets.ModelViewSet):
    """ViewSet for daily reports."""
    serializer_class = DailyReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['week_number', 'date']

    def get_queryset(self):
        return DailyReport.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        """Create daily report and update weekly report."""
        daily_report = serializer.save(student=self.request.user)
        # Update weekly report
        WeeklyReport.create_from_daily_reports(
            student=self.request.user,
            week_number=daily_report.week_number
        )

class WeeklyReportViewSet(viewsets.ModelViewSet):
    """ViewSet for weekly reports."""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['week_number']

    def get_queryset(self):
        """Get queryset for the current user."""
        if hasattr(self, 'request') and hasattr(self.request, 'user') and self.request.user.is_authenticated:
            return WeeklyReport.objects.filter(student=self.request.user)
        else:
            # Return empty queryset if no user
            return WeeklyReport.objects.none()

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action in ['create', 'update', 'partial_update']:
            return WeeklyReportCreateSerializer
        return WeeklyReportSerializer

    def perform_create(self, serializer):
        """Create weekly report with main job."""
        serializer.save(student=self.request.user)

    def perform_update(self, serializer):
        """Update weekly report and recalculate totals."""
        weekly_report = serializer.save()
        weekly_report.update_completion_status()
        weekly_report.calculate_total_hours()

    @action(detail=False, methods=['get', 'put'], url_path='week/(?P<week_number>[^/.]+)')
    def get_by_week_number(self, request, week_number=None):
        """Get or update weekly report by week number."""
        try:
            weekly_report = self.get_queryset().get(week_number=week_number)
            
            if request.method == 'GET':
                serializer = self.get_serializer(weekly_report)
                return Response(serializer.data)
            elif request.method == 'PUT':
                # Debug: Log the received data
                print(f"🔍 Received data for week {week_number}: {request.data}")
                
                # Use the create serializer for updates
                serializer = WeeklyReportCreateSerializer(weekly_report, data=request.data, partial=True)
                if serializer.is_valid():
                    updated_report = serializer.save()
                    # Return the updated data using the read serializer
                    read_serializer = self.get_serializer(updated_report)
                    return Response(read_serializer.data)
                else:
                    print(f"❌ Validation errors: {serializer.errors}")
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
        except WeeklyReport.DoesNotExist:
            if request.method == 'GET':
                return Response(
                    {"error": f"Weekly report for week {week_number} not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            elif request.method == 'PUT':
                # Debug: Log the received data
                print(f"🔍 Creating new report for week {week_number}: {request.data}")
                
                # Create new weekly report if it doesn't exist
                # First, try to get or create the weekly report to avoid duplicate
                try:
                    # Check if a weekly report already exists for this student and week
                    existing_report = WeeklyReport.objects.filter(
                        student=request.user,
                        week_number=week_number
                    ).first()
                    
                    if existing_report:
                        # Update existing report
                        serializer = WeeklyReportCreateSerializer(existing_report, data=request.data, partial=True)
                    else:
                        # Create new report
                        serializer = WeeklyReportCreateSerializer(data=request.data)
                    
                    if serializer.is_valid():
                        if existing_report:
                            weekly_report = serializer.save()
                        else:
                            weekly_report = serializer.save(student=request.user)
                        read_serializer = self.get_serializer(weekly_report)
                        return Response(read_serializer.data, status=status.HTTP_201_CREATED)
                    else:
                        print(f"❌ Validation errors: {serializer.errors}")
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                except Exception as e:
                    print(f"❌ Error creating/updating report: {e}")
                    return Response(
                        {"error": f"Error creating/updating report: {str(e)}"}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

    @action(detail=False, methods=['get'], url_path='week/(?P<week_number>[^/.]+)/download/pdf')
    def download_pdf(self, request, week_number=None):
        """Download weekly report as PDF."""
        try:
            weekly_report = self.get_queryset().get(week_number=week_number)
            pdf_content = export_weekly_report_pdf(weekly_report)
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="weekly_report_week_{week_number}.pdf"'
            return response
        except WeeklyReport.DoesNotExist:
            return Response(
                {"error": f"Weekly report for week {week_number} not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='week/(?P<week_number>[^/.]+)/download/docx')
    def download_docx(self, request, week_number=None):
        """Download weekly report as DOCX."""
        try:
            weekly_report = self.get_queryset().get(week_number=week_number)
            docx_content = export_weekly_report_docx(weekly_report)
            response = HttpResponse(docx_content, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            response['Content-Disposition'] = f'attachment; filename="weekly_report_week_{week_number}.docx"'
            return response
        except WeeklyReport.DoesNotExist:
            return Response(
                {"error": f"Weekly report for week {week_number} not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], url_path='week/(?P<week_number>[^/.]+)/enhance_with_ai')
    def enhance_by_week_number(self, request, week_number=None):
        """Enhance weekly report by week number"""
        try:
            # Ensure we have a valid user
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                return Response({
                    'success': False,
                    'message': 'Authentication required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get weekly report by week number
            try:
                weekly_report = self.get_queryset().get(week_number=week_number)
            except WeeklyReport.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'Weekly report for week {week_number} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            print(f"🔍 Enhancing weekly report for week {week_number} (ID: {weekly_report.id}) for user {request.user.id}")
            
            # Get additional instructions from request
            additional_instructions = request.data.get('additional_instructions', '')
            print(f"📝 Additional instructions: {additional_instructions}")
            
            # Prepare data for AI enhancement
            enhancement_data = self._prepare_enhancement_data(weekly_report)
            print(f"📊 Prepared enhancement data: {enhancement_data}")
            
            # Call Claude API
            enhanced_data = self._enhance_with_claude(enhancement_data, additional_instructions)
            
            if enhanced_data:
                print(f"✅ AI enhancement successful: {enhanced_data}")
                
                # Transform enhanced data to match serializer format
                transformed_data = self._transform_enhanced_data(enhanced_data, weekly_report)
                print(f"🔄 Transformed data: {transformed_data}")
                
                # Update the weekly report with enhanced data
                serializer = WeeklyReportCreateSerializer(
                    weekly_report,
                    data=transformed_data,
                    partial=True,
                    context={'request': request}
                )
                
                if serializer.is_valid():
                    enhanced_report = serializer.save()
                    return Response({
                        'success': True,
                        'message': 'Weekly report enhanced successfully',
                        'data': self.get_serializer(enhanced_report).data
                    })
                else:
                    print(f"❌ Serializer validation errors: {serializer.errors}")
                    return Response({
                        'success': False,
                        'message': 'Error saving enhanced report',
                        'errors': serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                print("❌ AI enhancement returned None")
                return Response({
                    'success': False,
                    'message': 'Failed to enhance report with AI'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            print(f"💥 Error in enhance_by_week_number: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'message': f'Error enhancing report: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def enhance_with_ai(self, request, pk=None):
        """Enhance weekly report using AI"""
        try:
            # Ensure we have a valid user
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                return Response({
                    'success': False,
                    'message': 'Authentication required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            weekly_report = self.get_object()
            print(f"🔍 Enhancing weekly report {pk} for user {request.user.id}")
            
            # Get additional instructions from request
            additional_instructions = request.data.get('additional_instructions', '')
            print(f"📝 Additional instructions: {additional_instructions}")
            
            # Prepare data for AI enhancement
            enhancement_data = self._prepare_enhancement_data(weekly_report)
            print(f"📊 Prepared enhancement data: {enhancement_data}")
            
            # Call Claude API
            enhanced_data = self._enhance_with_claude(enhancement_data, additional_instructions)
            
            if enhanced_data:
                print(f"✅ AI enhancement successful: {enhanced_data}")
                
                # Transform enhanced data to match serializer format
                transformed_data = self._transform_enhanced_data(enhanced_data, weekly_report)
                print(f"🔄 Transformed data: {transformed_data}")
                
                # Update the weekly report with enhanced data
                serializer = WeeklyReportCreateSerializer(
                    weekly_report,
                    data=transformed_data,
                    partial=True,
                    context={'request': request}
                )
                
                if serializer.is_valid():
                    enhanced_report = serializer.save()
                    return Response({
                        'success': True,
                        'message': 'Weekly report enhanced successfully',
                        'data': self.get_serializer(enhanced_report).data
                    })
                else:
                    print(f"❌ Serializer validation errors: {serializer.errors}")
                    return Response({
                        'success': False,
                        'message': 'Error saving enhanced report',
                        'errors': serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                print("❌ AI enhancement returned None")
                return Response({
                    'success': False,
                    'message': 'Failed to enhance report with AI'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            print(f"💥 Error in enhance_with_ai: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'message': f'Error enhancing report: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _prepare_enhancement_data(self, weekly_report):
        """Prepare data for AI enhancement"""
        # Get daily reports using the correct method
        daily_reports = weekly_report.get_daily_reports()
        
        # Get main job and operations
        main_job = weekly_report.main_job
        operations = []
        if main_job:
            operations = main_job.operations.all().order_by('step_number')
        
        # Prepare daily data
        daily_data = []
        for report in daily_reports:
            daily_data.append({
                'day': report.date.strftime('%A'),  # Use 'date' instead of 'report_date'
                'date': report.date.strftime('%Y-%m-%d'),
                'description': report.description or '',
                'hours_worked': float(report.hours_spent)  # Use 'hours_spent' instead of 'hours_worked'
            })
        
        # Prepare operations data
        operations_data = []
        for operation in operations:
            operations_data.append({
                'step_number': operation.step_number,
                'operation_description': operation.operation_description or '',
                'tools_used': operation.tools_used or ''
            })
        
        return {
            'main_job_title': main_job.title if main_job else '',
            'daily_reports': daily_data,
            'operations': operations_data,
            'week_number': weekly_report.week_number
        }
    
    def _enhance_with_claude(self, data, additional_instructions):
        """Enhance data using Anthropic Claude API"""
        try:
            # Prepare prompt
            prompt = self._create_enhancement_prompt(data, additional_instructions)
            
            # Call Claude API (using Claude 3 Haiku - cheapest model)
            response = anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse response
            enhanced_content = response.content[0].text
            
            # Parse the JSON response
            try:
                enhanced_data = json.loads(enhanced_content)
                return enhanced_data
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', enhanced_content, re.DOTALL)
                if json_match:
                    enhanced_data = json.loads(json_match.group())
                    return enhanced_data
                else:
                    print(f"Failed to parse Claude response: {enhanced_content}")
                    return None
                    
        except Exception as e:
            print(f"Claude API Error: {str(e)}")
            return None
    
    def _create_enhancement_prompt(self, data, additional_instructions):
        """Create the enhancement prompt for Claude"""
        
        # Prepare daily reports text
        daily_text = ""
        for daily in data['daily_reports']:
            daily_text += f"Day: {daily['day']} ({daily['date']})\n"
            daily_text += f"Hours: {daily['hours_worked']}\n"
            daily_text += f"Description: {daily['description']}\n\n"
        
        # Prepare operations text
        operations_text = ""
        for op in data['operations']:
            operations_text += f"Step {op['step_number']}: {op['operation_description']}\n"
            operations_text += f"Tools: {op['tools_used']}\n\n"
        
        prompt = f"""
You are an expert technical writer specializing in practical training reports. Your task is to enhance a weekly practical training report to make it more professional, technical, and comprehensive.

CONTEXT:
- Main Job Title: {data['main_job_title']}
- Week Number: {data['week_number']}
- This is for a practical training/internship report

CURRENT DATA:
{daily_text}

CURRENT OPERATIONS:
{operations_text}

ENHANCEMENT REQUIREMENTS:

1. DAILY DESCRIPTIONS:
   - Convert any Swahili text to professional English
   - Make each description 2-3 sentences long (50-80 words)
   - Include specific technical details, tools used, and learning outcomes
   - Focus on practical skills gained and tasks performed
   - Use professional technical language
   - Example good description: "Conducted detailed analysis of electrical circuit components using multimeter and oscilloscope. Successfully identified and resolved voltage regulation issues in the amplifier circuit. Gained hands-on experience with circuit troubleshooting and component testing procedures."

2. OPERATIONS:
   - Ensure at least 4 detailed operation steps
   - Each step should be specific and actionable
   - Include technical tools and equipment used
   - Make steps sequential and logical
   - Example good step: "Step 1: Set up the oscilloscope and connect probes to the circuit test points. Calibrate the instrument to measure voltage ranges between 0-12V DC."

3. MAIN JOB TITLE:
   - Make it more specific and technical
   - Include the main focus area

ADDITIONAL INSTRUCTIONS: {additional_instructions}

CRITICAL: Return ONLY a valid JSON object in this EXACT format:
{{
    "main_job_title": "Enhanced specific technical job title",
    "daily_reports": [
        {{
            "day": "Monday",
            "date": "2025-01-20",
            "description": "Enhanced professional technical description (2-3 sentences, 50-80 words)",
            "hours_worked": 8
        }},
        {{
            "day": "Tuesday", 
            "date": "2025-01-21",
            "description": "Enhanced professional technical description (2-3 sentences, 50-80 words)",
            "hours_worked": 8
        }},
        {{
            "day": "Wednesday",
            "date": "2025-01-22", 
            "description": "Enhanced professional technical description (2-3 sentences, 50-80 words)",
            "hours_worked": 8
        }},
        {{
            "day": "Thursday",
            "date": "2025-01-23",
            "description": "Enhanced professional technical description (2-3 sentences, 50-80 words)", 
            "hours_worked": 8
        }},
        {{
            "day": "Friday",
            "date": "2025-01-24",
            "description": "Enhanced professional technical description (2-3 sentences, 50-80 words)",
            "hours_worked": 8
        }}
    ],
    "operations": [
        {{
            "step_number": 1,
            "operation_description": "Detailed technical operation step with specific actions and procedures",
            "tools_used": "Specific tools, equipment, and software used"
        }},
        {{
            "step_number": 2,
            "operation_description": "Detailed technical operation step with specific actions and procedures",
            "tools_used": "Specific tools, equipment, and software used"
        }},
        {{
            "step_number": 3,
            "operation_description": "Detailed technical operation step with specific actions and procedures",
            "tools_used": "Specific tools, equipment, and software used"
        }},
        {{
            "step_number": 4,
            "operation_description": "Detailed technical operation step with specific actions and procedures",
            "tools_used": "Specific tools, equipment, and software used"
        }}
    ]
}}

IMPORTANT RULES:
- Return ONLY the JSON object, no additional text
- Ensure all descriptions are professional and technical
- Include specific technical details and learning outcomes
- Make descriptions informative but concise (2-3 sentences)
- Ensure operations have at least 4 detailed steps
- Use proper technical terminology
- Maintain accuracy to the original content while enhancing it
"""

        return prompt

    def _transform_enhanced_data(self, enhanced_data, weekly_report):
        """Transform enhanced data to match serializer format"""
        transformed = {
            'main_job_title': enhanced_data.get('main_job_title', ''),
        }
        
        # Transform daily reports to individual fields
        daily_reports = enhanced_data.get('daily_reports', [])
        for daily in daily_reports:
            day = daily.get('day', '').lower()
            description = daily.get('description', '')
            hours = daily.get('hours_worked', 0)
            
            if day == 'monday':
                transformed['daily_monday'] = description
                transformed['hours_monday'] = hours
            elif day == 'tuesday':
                transformed['daily_tuesday'] = description
                transformed['hours_tuesday'] = hours
            elif day == 'wednesday':
                transformed['daily_wednesday'] = description
                transformed['hours_wednesday'] = hours
            elif day == 'thursday':
                transformed['daily_thursday'] = description
                transformed['hours_thursday'] = hours
            elif day == 'friday':
                transformed['daily_friday'] = description
                transformed['hours_friday'] = hours
        
        # Transform operations
        operations = enhanced_data.get('operations', [])
        if operations:
            transformed['main_job'] = {
                'title': enhanced_data.get('main_job_title', ''),
                'operations': operations
            }
        
        return transformed


class MainJobViewSet(viewsets.ModelViewSet):
    """ViewSet for main jobs - one per weekly report."""
    serializer_class = MainJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['weekly_report']

    def get_queryset(self):
        return MainJob.objects.filter(weekly_report__student=self.request.user)

class MainJobOperationViewSet(viewsets.ModelViewSet):
    """ViewSet for main job operations."""
    serializer_class = MainJobOperationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['main_job', 'step_number']

    def get_queryset(self):
        return MainJobOperation.objects.filter(main_job__weekly_report__student=self.request.user)

    def perform_create(self, serializer):
        """Create operation linked to main job."""
        main_job_id = self.kwargs.get('main_job_id')
        main_job = get_object_or_404(MainJob, id=main_job_id, weekly_report__student=self.request.user)
        serializer.save(main_job=main_job)

    def list(self, request, *args, **kwargs):
        """List operations for a specific main job."""
        main_job_id = self.kwargs.get('main_job_id')
        main_job = get_object_or_404(MainJob, id=main_job_id, weekly_report__student=self.request.user)
        operations = self.get_queryset().filter(main_job=main_job)
        serializer = self.get_serializer(operations, many=True)
        return Response(serializer.data) 

class MainJobOperationsViewSet(viewsets.ModelViewSet):
    """ViewSet for managing operations within a specific main job."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get operations for the specific main job."""
        main_job_id = self.kwargs.get('main_job_id')
        main_job = get_object_or_404(MainJob, id=main_job_id, weekly_report__student=self.request.user)
        return MainJobOperation.objects.filter(main_job=main_job).order_by('step_number')

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'create':
            return MainJobOperationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MainJobOperationUpdateSerializer
        return MainJobOperationSerializer

    def get_serializer_context(self):
        """Add main_job to serializer context."""
        context = super().get_serializer_context()
        main_job_id = self.kwargs.get('main_job_id')
        main_job = get_object_or_404(MainJob, id=main_job_id, weekly_report__student=self.request.user)
        context['main_job'] = main_job
        return context

    def perform_create(self, serializer):
        """Create operation linked to the specific main job."""
        main_job_id = self.kwargs.get('main_job_id')
        main_job = get_object_or_404(MainJob, id=main_job_id, weekly_report__student=self.request.user)
        serializer.save(main_job=main_job)

    def perform_update(self, serializer):
        """Update operation."""
        serializer.save()

    def perform_destroy(self, instance):
        """Delete operation."""
        instance.delete()



class MainJobDetailViewSet(viewsets.ModelViewSet):
    """ViewSet for managing main job details."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get main jobs for the authenticated user."""
        return MainJob.objects.filter(weekly_report__student=self.request.user)

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action in ['update', 'partial_update']:
            return MainJobUpdateSerializer
        return MainJobDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        """Get main job with operations."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """Update main job title."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Return the updated data with operations
        detail_serializer = MainJobDetailSerializer(instance)
        return Response(detail_serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Partial update main job title."""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs) 