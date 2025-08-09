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
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != 'your-api-key-here':
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    anthropic_client = None

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
            
            # Save original inputs before enhancement
            self._save_original_inputs(weekly_report, enhancement_data, additional_instructions)
            
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
                if anthropic_client is None:
                    return Response({
                        'success': False,
                        'message': 'AI enhancement not available - no valid API key configured. Please set ANTHROPIC_API_KEY environment variable.',
                        'error_type': 'missing_api_key'
                    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                else:
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
            
            # Save original inputs before enhancement
            self._save_original_inputs(weekly_report, enhancement_data, additional_instructions)
            
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
                if anthropic_client is None:
                    return Response({
                        'success': False,
                        'message': 'AI enhancement not available - no valid API key configured. Please set ANTHROPIC_API_KEY environment variable.',
                        'error_type': 'missing_api_key'
                    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                else:
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
        
        # Get user profile data
        user = weekly_report.student
        user_program = ''
        company_name = ''
        
        try:
            profile = user.profile
            user_program = profile.get_program_display() if profile.program else ''
            company_name = profile.company_name or ''
        except:
            pass  # User might not have a profile
        
        # Prepare daily data with original user inputs
        daily_data = []
        for report in daily_reports:
            daily_data.append({
                'day': report.date.strftime('%A'),  # Use 'date' instead of 'report_date'
                'date': report.date.strftime('%Y-%m-%d'),
                'description': report.description or '',
                'hours_worked': float(report.hours_spent),  # Use 'hours_spent' instead of 'hours_worked'
                'original_hours': float(report.hours_spent),  # Preserve original hours
                'original_description': report.description or ''  # Preserve original description
            })
        
        # Prepare operations data with original user inputs
        operations_data = []
        for operation in operations:
            operations_data.append({
                'step_number': operation.step_number,
                'operation_description': operation.operation_description or '',
                'tools_used': operation.tools_used or '',
                'original_operation_description': operation.operation_description or '',
                'original_tools_used': operation.tools_used or ''
            })
        
        return {
            'main_job_title': main_job.title if main_job else '',
            'daily_reports': daily_data,
            'operations': operations_data,
            'week_number': weekly_report.week_number,
            'user_program': user_program,
            'company_name': company_name
        }
    
    def _enhance_with_claude(self, data, additional_instructions):
        """Enhance data using Anthropic Claude API"""
        try:
            # Check if Claude API is available
            if anthropic_client is None:
                print("❌ Claude API not available - no valid API key provided")
                return None
            
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
You are a {data['user_program']} student at University of Dar es Salaam completing practical training at {data['company_name']}. Enhance this weekly report to make it more professional, technical, and comprehensive for Week {data['week_number']} of 8 while respecting the user's original inputs.

STUDENT CONTEXT:
- Program: {data['user_program']} 
- University: University of Dar es Salaam
- Company: {data['company_name']}
- Current Role: {data['main_job_title'] or 'Not specified - suggest based on daily work'}

ORIGINAL USER INPUTS:
Daily Work: {daily_text}
Main Tasks: {operations_text}

ENHANCEMENT GUIDELINES:

1. **RESPECT USER INPUTS**: Use the user's original hours, descriptions, and operations as your foundation. Enhance them to be more proffesional and technical report, don't completely replace them.

2. **HOURS HANDLING**: 
   - Use the exact hours the user provided for each day (see original_hours in data)
   - If user didn't specify hours, use 5-9 hours range (prefer 6,7,8 hours dont use same to all days)
   - Don't change hours unless user specifically requests it or it was empty

3. **MAIN JOB TITLE**:
   - If user provided a title: Enhance it to be more specific and technical but only when it necessary 
   - If user didn't provide title: Suggest one based on the most interesting/complex daily work from this week
   - Prefer jobs that involve diagrams, technical processes, or hands-on work
   - Look at the daily descriptions to identify the main focus area,the main job

4. **OPERATIONS**:
   - If user provided operations: Enhance each step while keeping their original approach
   - If user didn't provide operations: Create 4-5 steps based on the main job title
   - Don't force exactly 4 steps - match the complexity of the actual work
   - make sure be systematic and sequetial,elaborate clearly each steps 

5. **DAILY DESCRIPTIONS**:
   - Enhance user's original descriptions (2-3 sentences, 50-80 words)
   - Keep their main activities and learning points
   - Add technical details, tools used, and learning outcomes
   - Example good description: "Conducted detailed analysis of electrical circuit components using multimeter and oscilloscope. Successfully identified and resolved voltage regulation issues in the amplifier circuit.

6. **USER INSTRUCTIONS**: {additional_instructions}
   - Follow any specific language, length, or style requests if stated 
   - Respect any tools, hours, or approach preferences
   - Use any provided examples as reference for writing style

WRITING STYLE:
- Write as a genuine student would but technical
- Ensure all descriptions are professional and technical 
- Show progressive skill development
- Mix technical terms with everyday language
- Make it more specific and technical but not robotic generated
- Use proper technical terminology
Return only this JSON format:

{{
    "main_job_title": "Enhanced or suggested job title based on daily work",
    "daily_reports": [
        {{
            "day": "Monday",
            "date": "2025-01-20", 
            "description": "Enhanced description based on user's original input",
            "hours_worked": "Use user's original hours, default to 8 if not specified"
        }},
        {{
            "day": "Tuesday",
            "date": "2025-01-21",
            "description": "Enhanced description based on user's original input", 
            "hours_worked": "Use user's original hours, default to 8 if not specified"
        }},
        {{
            "day": "Wednesday", 
            "date": "2025-01-22",
            "description": "Enhanced description based on user's original input",
            "hours_worked": "Use user's original hours, default to 8 if not specified"
        }},
        {{
            "day": "Thursday",
            "date": "2025-01-23", 
            "description": "Enhanced description based on user's original input",
            "hours_worked": "Use user's original hours, default to 8 if not specified"
        }},
        {{
            "day": "Friday",
            "date": "2025-01-24",
            "description": "Enhanced description based on user's original input",
            "hours_worked": "Use user's original hours, default to 8 if not specified"
        }}
    ],
    "operations": [
        {{
            "step_number": 1,
            "operation_description": "Enhanced step based on user's original or created from daily work",
            "tools_used": "Tools and equipment used"
        }}
        // Add more steps as needed (4-6 total)
    ]
}}
"""

        return prompt
    
    def _save_original_inputs(self, weekly_report, data, additional_instructions):
        """Save original user inputs before enhancement for potential reset."""
        try:
            from apps.reports.models import OriginalUserInputs
            
            # Prepare original data for storage
            original_daily_reports = []
            for daily in data.get('daily_reports', []):
                original_daily_reports.append({
                    'day': daily.get('day'),
                    'date': daily.get('date'),
                    'description': daily.get('original_description', daily.get('description', '')),
                    'hours_worked': daily.get('original_hours', daily.get('hours_worked', 0))
                })
            
            original_operations = []
            for op in data.get('operations', []):
                original_operations.append({
                    'step_number': op.get('step_number'),
                    'operation_description': op.get('original_operation_description', op.get('operation_description', '')),
                    'tools_used': op.get('original_tools_used', op.get('tools_used', ''))
                })
            
            # Create or update original inputs record
            original_inputs, created = OriginalUserInputs.objects.get_or_create(
                weekly_report=weekly_report,
                defaults={
                    'original_main_job_title': data.get('main_job_title', ''),
                    'original_daily_reports': original_daily_reports,
                    'original_operations': original_operations,
                    'enhancement_instructions': additional_instructions
                }
            )
            
            if not created:
                # Update existing record
                original_inputs.original_main_job_title = data.get('main_job_title', '')
                original_inputs.original_daily_reports = original_daily_reports
                original_inputs.original_operations = original_operations
                original_inputs.enhancement_instructions = additional_instructions
                original_inputs.save()
            
            print(f"💾 Saved original inputs for weekly report {weekly_report.id}")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not save original inputs: {str(e)}")
            # Don't fail the enhancement if saving original inputs fails

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
        # Audit before deleting to prevent silent loss
        try:
            from apps.core.audit import log_change
            log_change(
                model_name='MainJobOperation',
                action='delete',
                payload={
                    'id': instance.id,
                    'main_job_id': instance.main_job_id,
                    'step_number': instance.step_number,
                    'operation_description': instance.operation_description,
                    'tools_used': instance.tools_used,
                }
            )
        except Exception:
            pass
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