from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django_filters import rest_framework as filters
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from .models import (
    AiChatMessage, AiChatSession, DailyReport, WeeklyReport, MainJob,
    MainJobOperation, OriginalUserInputs, get_week_dates,
)
from .serializers import (
    DailyReportSerializer, WeeklyReportSerializer, WeeklyReportCreateSerializer,
    MainJobSerializer, MainJobOperationSerializer, MainJobDetailSerializer,
    MainJobUpdateSerializer, MainJobOperationCreateSerializer, MainJobOperationUpdateSerializer
)
from apps.exporter.services import export_weekly_report_pdf, export_weekly_report_docx
from apps.exporter.views import (
    _export_token_cost, _check_export_tokens, _deduct_export_tokens,
)
import anthropic
import json
import os
import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone

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
        except WeeklyReport.DoesNotExist:
            return Response(
                {"error": f"Weekly report for week {week_number} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Enforce the same export pricing as /api/export/*: 100 normal, 200 enhanced.
        token_cost = _export_token_cost(weekly_report)
        denied = _check_export_tokens(request.user, token_cost)
        if denied is not None:
            return denied

        try:
            pdf_content = export_weekly_report_pdf(weekly_report)
            _deduct_export_tokens(request.user, token_cost)
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="weekly_report_week_{week_number}.pdf"'
            return response
        except Exception as e:
            return Response(
                {"error": "Unable to generate PDF report. Please try again or contact support if the issue persists."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='week/(?P<week_number>[^/.]+)/download/docx')
    def download_docx(self, request, week_number=None):
        """Download weekly report as DOCX."""
        try:
            weekly_report = self.get_queryset().get(week_number=week_number)
        except WeeklyReport.DoesNotExist:
            return Response(
                {"error": f"Weekly report for week {week_number} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Enforce the same export pricing as /api/export/*: 100 normal, 200 enhanced.
        token_cost = _export_token_cost(weekly_report)
        denied = _check_export_tokens(request.user, token_cost)
        if denied is not None:
            return denied

        try:
            docx_content = export_weekly_report_docx(weekly_report)
            _deduct_export_tokens(request.user, token_cost)
            response = HttpResponse(docx_content, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            response['Content-Disposition'] = f'attachment; filename="weekly_report_week_{week_number}.docx"'
            return response
        except Exception as e:
            return Response(
                {"error": "Unable to generate DOCX report. Please try again or contact support if the issue persists."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
            
            # Call Claude API (via VPS or direct)
            enhanced_data = self._enhance_report(enhancement_data, additional_instructions, request.user.id)
            
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
            
            # Call Claude API (via VPS or direct)
            enhanced_data = self._enhance_report(enhancement_data, additional_instructions, request.user.id)
            
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
    
    @action(detail=False, methods=['post'], url_path='week/(?P<week_number>[^/.]+)/reset_to_original')
    def reset_to_original(self, request, week_number=None):
        """Reset weekly report to original user inputs before AI enhancement"""
        try:
            # Ensure authenticated
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                return Response({
                    'success': False,
                    'message': 'Authentication required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get weekly report
            try:
                weekly_report = self.get_queryset().get(week_number=week_number)
            except WeeklyReport.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'Weekly report for week {week_number} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get original inputs
            from apps.reports.models import OriginalUserInputs
            try:
                original_inputs = OriginalUserInputs.objects.get(
                    weekly_report=weekly_report,
                    is_reset_available=True
                )
            except OriginalUserInputs.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'No original inputs available for reset or reset not allowed'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Transform original data back to serializer format
            transformed_data = self._transform_original_data(original_inputs)
            
            # Update the weekly report with original data
            serializer = WeeklyReportCreateSerializer(
                weekly_report,
                data=transformed_data,
                partial=True,
                context={'request': request}
            )
            
            if serializer.is_valid():
                restored_report = serializer.save()
                
                # Mark reset as unavailable (can only reset once)
                original_inputs.is_reset_available = False
                original_inputs.save()
                
                return Response({
                    'success': True,
                    'message': 'Weekly report reset to original inputs successfully',
                    'data': self.get_serializer(restored_report).data
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Error restoring original inputs',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            print(f"💥 Error in reset_to_original: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'message': f'Error resetting report: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='vps-health')
    def vps_health_check(self, request):
        """Check if VPS AI service is available"""
        if not settings.VPS_AI_SERVICE_ENABLED:
            return Response({
                'status': 'disabled',
                'message': 'VPS AI service is disabled in settings'
            })
        
        try:
            response = requests.get(
                f"{settings.VPS_AI_SERVICE_URL}/api/weekly/health",
                timeout=5
            )
            
            if response.status_code == 200:
                return Response({
                    'status': 'healthy',
                    'vps_url': settings.VPS_AI_SERVICE_URL,
                    'vps_response': response.json()
                })
            else:
                return Response({
                    'status': 'unhealthy',
                    'vps_url': settings.VPS_AI_SERVICE_URL,
                    'http_status': response.status_code
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
        except Exception as e:
            return Response({
                'status': 'unreachable',
                'vps_url': settings.VPS_AI_SERVICE_URL,
                'error': str(e)
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    def _prepare_enhancement_data(self, weekly_report):
        """Prepare data for AI enhancement"""
        # Get daily reports using the correct method
        daily_reports = weekly_report.get_daily_reports()

        # Get main job and operations (a brand new week has no main job yet)
        main_job = MainJob.objects.filter(weekly_report=weekly_report).first()
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
        
        # Always send the full Monday-Friday week so the AI knows which days
        # are still empty and can ask the user about them. Rows are matched by
        # date first and by weekday as a fallback, so entries recorded against a
        # different calendar (e.g. last year's training dates) are still shown
        # instead of the enhancement seeing an empty week.
        from datetime import timedelta
        try:
            week_dates = get_week_dates(weekly_report.week_number, timezone.now().year)
        except ValueError:
            week_dates = None

        by_date = {report.date: report for report in daily_reports}
        by_weekday = {}
        for report in daily_reports:
            weekday = report.date.weekday()
            if 0 <= weekday <= 4 and weekday not in by_weekday:
                by_weekday[weekday] = report

        daily_data = []
        if week_dates:
            for offset in range(5):
                day_date = week_dates['start_date'] + timedelta(days=offset)
                report = by_date.get(day_date) or by_weekday.get(offset)
                description = (report.description if report else '') or ''
                hours = float(report.hours_spent) if report else 0.0
                daily_data.append({
                    'day': day_date.strftime('%A'),
                    'date': day_date.strftime('%Y-%m-%d'),
                    'description': description,
                    'hours_worked': hours,
                    'original_hours': hours,
                    'original_description': description
                })
        else:
            for report in daily_reports:
                daily_data.append({
                    'day': report.date.strftime('%A'),
                    'date': report.date.strftime('%Y-%m-%d'),
                    'description': report.description or '',
                    'hours_worked': float(report.hours_spent),
                    'original_hours': float(report.hours_spent),
                    'original_description': report.description or ''
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
        """Enhance data using Anthropic Claude API (fallback)"""
        print("🤖 Using direct Claude API (fallback)")
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
    
    def _enhance_via_vps(self, data, additional_instructions, user_id):
        """Enhance data via VPS AI service"""
        if not settings.VPS_AI_SERVICE_ENABLED:
            print("⚠️ VPS AI service disabled in settings")
            return None
        
        payload = {
            "user_id": user_id,
            "report_data": {
                "week_number": data.get('week_number'),
                "main_job_title": data.get('main_job_title', ''),
                "daily_reports": data.get('daily_reports', []),
                "operations": data.get('operations', []),
                "user_program": data.get('user_program', ''),
                "company_name": data.get('company_name', ''),
                "additional_instructions": additional_instructions
            }
        }
        
        try:
            print(f"🌐 Calling VPS AI service at {settings.VPS_AI_SERVICE_URL}")
            response = requests.post(
                f"{settings.VPS_AI_SERVICE_URL}/api/weekly/enhance",
                json=payload,
                headers={"X-API-Key": settings.VPS_API_KEY},
                timeout=settings.VPS_REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ VPS enhancement successful, tokens used: {result.get('tokens_used')}")
                    return result.get('enhanced_data')
                else:
                    print(f"❌ VPS enhancement failed: {result.get('error')}")
                    return None
            else:
                print(f"❌ VPS returned status {response.status_code}: {response.text}")
                return None
        except requests.exceptions.Timeout:
            print("⏱️ VPS request timed out")
            return None
        except requests.exceptions.ConnectionError:
            print("🔌 VPS connection failed")
            return None
        except Exception as e:
            print(f"💥 VPS enhancement error: {str(e)}")
            return None
    
    def _enhance_report(self, data, additional_instructions, user_id):
        """Enhance report using VPS or fallback to direct Claude"""
        # Try VPS first
        if settings.VPS_AI_SERVICE_ENABLED:
            enhanced_data = self._enhance_via_vps(data, additional_instructions, user_id)
            if enhanced_data:
                return enhanced_data
            print("⚠️ VPS failed, falling back to direct Claude API")
        
        # Fallback to direct Claude
        return self._enhance_with_claude(data, additional_instructions)
    
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
                    'user': weekly_report.student,
                    'week_number': weekly_report.week_number,
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
            
            print(f"Saved original inputs for weekly report {weekly_report.id}")
            
        except Exception as e:
            # Don't fail the enhancement if saving original inputs fails
            print(f"Warning: Could not save original inputs: {str(e)}")

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
    
    def _transform_original_data(self, original_inputs):
        """Transform original inputs data to serializer format"""
        transformed = {
            'main_job_title': original_inputs.original_main_job_title or '',
        }
        
        # Transform daily reports from JSON to individual fields
        daily_reports = original_inputs.original_daily_reports if isinstance(original_inputs.original_daily_reports, list) else []
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
        operations = original_inputs.original_operations if isinstance(original_inputs.original_operations, list) else []
        if operations:
            transformed['main_job'] = {
                'title': original_inputs.original_main_job_title or '',
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

    def get_object(self):
        """Get the specific operation for update/delete."""
        queryset = self.get_queryset()
        pk = self.kwargs.get('pk')
        print(f"🔍 MainJobOperationsViewSet.get_object: main_job_id={self.kwargs.get('main_job_id')}, pk={pk}")
        print(f"🔍 Queryset: {queryset}")
        obj = get_object_or_404(queryset, pk=pk)
        print(f"🔍 Found object: {obj}")
        return obj

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


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def ai_fetch_report_data(request):
    """Endpoint for AI service to fetch report data for enhancement"""
    try:
        user_id = request.GET.get('user_id')
        week_number = request.GET.get('week_number')

        if not all([user_id, week_number]):
            return Response({
                'success': False,
                'error': 'Missing required parameters: user_id, week_number'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get user and report
        user = User.objects.get(id=user_id)
        weekly_report = WeeklyReport.objects.get(student=user, week_number=week_number)

        # Prepare data for AI enhancement
        viewset = WeeklyReportViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        enhancement_data = viewset._prepare_enhancement_data(weekly_report)

        return Response({
            'success': True,
            'data': enhancement_data
        })

    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except WeeklyReport.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Weekly report not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def ai_save_enhanced_report(request):
    """Endpoint for AI service to save enhanced report"""
    try:
        user_id = request.data.get('user_id')
        week_number = request.data.get('week_number')
        enhanced_data = request.data.get('enhanced_data')

        if not all([user_id, week_number, enhanced_data]):
            return Response({
                'success': False,
                'error': 'Missing required fields: user_id, week_number, enhanced_data'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get user and report
        user = User.objects.get(id=user_id)
        weekly_report = WeeklyReport.objects.get(student=user, week_number=week_number)

        # Transform and save enhanced data
        viewset = WeeklyReportViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        transformed_data = viewset._transform_enhanced_data(enhanced_data, weekly_report)
        serializer = WeeklyReportCreateSerializer(
            weekly_report,
            data=transformed_data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Enhanced report saved successfully'
            })
        else:
            return Response({
                'success': False,
                'error': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except WeeklyReport.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Weekly report not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _ai_viewset(request):
    """WeeklyReportViewSet instance bound to the request (helpers are instance methods)."""
    viewset = WeeklyReportViewSet()
    viewset.request = request
    viewset.format_kwarg = None
    return viewset


def _session_owner_cache_key(session_id):
    return f'weekly_ai_session_owner:{session_id}'


def _assistant_content(ai_message, question):
    """The exact text the chat UI shows for one assistant turn."""
    ai_message = (ai_message or '').strip()
    question = (question or '').strip()
    if ai_message and question and ai_message != question:
        return f"{ai_message}\n\n{question}"
    return question or ai_message or 'How can I help you enhance this report?'


def _get_chat_session(user, week_number):
    return AiChatSession.objects.filter(
        student=user, week_number=week_number
    ).first()


def _clear_pending(chat):
    AiChatMessage.objects.filter(session=chat, is_pending=True).update(is_pending=False)


def _save_chat_message(chat, role, content, message_type='text', meta=None, pending=False):
    return AiChatMessage.objects.create(
        session=chat,
        role=role,
        content=content,
        message_type=message_type,
        meta=meta or {},
        is_pending=pending
    )


def _chat_transcript(chat):
    """Earlier messages used to seed a brand new AI session for the same week."""
    if chat is None:
        return []
    return [
        {'role': message.role, 'content': message.content}
        for message in chat.messages.all().order_by('created_at')
        if message.message_type not in ('error', 'separator')
        and (message.content or '').strip()
    ]


def _ai_session_alive(session_id):
    """Ask the AI service whether a session can still be resumed."""
    if not session_id:
        return False
    url = f"{settings.VPS_AI_SERVICE_URL}/api/weekly/session/{session_id}"
    try:
        response = requests.get(
            url,
            headers={'X-API-Key': settings.VPS_API_KEY},
            timeout=15
        )
        return response.status_code == 200 and bool(response.json().get('exists'))
    except (requests.exceptions.RequestException, ValueError):
        return False


# Shown in the chat when something fails: what happened, then what to do
# about it - a dead end with no next step is what makes people stuck.
RETRY_RECOMMENDATIONS = [
    'Send your message again - this is usually temporary.',
    'Wait a minute and try once more if it keeps failing.',
    'Your report and chat history are saved - nothing is lost.',
]
SESSION_EXPIRED_RECOMMENDATIONS = [
    'Click "New" in the top corner, then pick this week again to start a fresh chat.',
    'Your report and chat history are saved - nothing is lost.',
]
AI_SERVICE_DOWN_RECOMMENDATIONS = [
    'The AI service may be restarting - wait a moment and send your message again.',
    'If it keeps happening, let your supervisor know the AI service is offline.',
    'Your report and chat history are saved - nothing is lost.',
]

# The divider written into the chat when a user opens a fresh enhancement
# session on top of a previously completed one.
NEW_SESSION_SEPARATOR = '---------- NEW SESSION ----------'


def _ai_error(code, message, recommendations=None):
    return {
        'success': False,
        'code': code,
        'message': message,
        'recommendations': recommendations or RETRY_RECOMMENDATIONS,
    }


def _is_session_expired(error):
    data = getattr(error, 'data', None)
    return isinstance(data, dict) and data.get('code') == 'SESSION_EXPIRED'


def _call_ai_service(path, payload):
    """Forward a request to the AI service.

    Returns (data, None) on success or (None, Response) with a user friendly
    error when the AI service is unreachable or reports a failure.
    """
    url = f"{settings.VPS_AI_SERVICE_URL}{path}"
    try:
        response = requests.post(
            url,
            json=payload,
            headers={'X-API-Key': settings.VPS_API_KEY},
            timeout=settings.VPS_REQUEST_TIMEOUT
        )
    except requests.exceptions.Timeout:
        return None, Response(
            _ai_error(
                'AI_TIMEOUT',
                'The AI service took too long to respond. Please try again.'
            ),
            status=status.HTTP_504_GATEWAY_TIMEOUT
        )
    except requests.exceptions.RequestException:
        return None, Response(
            _ai_error(
                'AI_UNAVAILABLE',
                'The AI service is unavailable right now. Please try again later.',
                AI_SERVICE_DOWN_RECOMMENDATIONS
            ),
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    if response.status_code != 200:
        return None, Response(
            _ai_error(
                'AI_BAD_RESPONSE',
                f'The AI service returned an unexpected response '
                f'(HTTP {response.status_code}). Please try again.'
            ),
            status=status.HTTP_502_BAD_GATEWAY
        )

    try:
        data = response.json()
    except ValueError:
        return None, Response(
            _ai_error(
                'AI_BAD_RESPONSE',
                'The AI service returned an invalid response. Please try again.'
            ),
            status=status.HTTP_502_BAD_GATEWAY
        )

    if not data.get('success'):
        service_error = (data.get('error') or '').strip()
        if service_error.lower() == 'invalid session id':
            # The service lost the session (restart or TTL) - callers may
            # rebuild it from the stored transcript and retry.
            return None, Response(
                _ai_error(
                    'SESSION_EXPIRED',
                    'This chat session has expired, so it cannot be continued as is.',
                    SESSION_EXPIRED_RECOMMENDATIONS
                ),
                status=status.HTTP_502_BAD_GATEWAY
            )
        return None, Response(
            _ai_error(
                'AI_ENHANCE_FAILED',
                service_error or 'The AI enhancement failed. Please try again.'
            ),
            status=status.HTTP_502_BAD_GATEWAY
        )

    return data, None


def _recover_answer_session(request, chat, user_content):
    """The AI service lost this session (restart or TTL) - rebuild it from the
    stored transcript and replay the answer so the chat continues seamlessly."""
    weekly_report = WeeklyReport.objects.filter(
        student=request.user, week_number=chat.week_number
    ).first()
    if weekly_report is None:
        return None, Response(
            _ai_error(
                'SESSION_EXPIRED',
                'This chat session has expired and there is no report to rebuild it from.',
                SESSION_EXPIRED_RECOMMENDATIONS
            ),
            status=status.HTTP_409_CONFLICT
        )

    viewset = _ai_viewset(request)
    enhancement_data = viewset._prepare_enhancement_data(weekly_report)
    original_inputs = OriginalUserInputs.objects.filter(
        weekly_report=weekly_report
    ).first()
    payload = {
        'user_id': request.user.id,
        'mode': 'converse',
        'report_data': _build_report_payload(
            weekly_report,
            enhancement_data,
            (original_inputs.enhancement_instructions if original_inputs else '') or ''
        ),
        'conversation_history': _chat_transcript(chat),
        'user_message': user_content,
    }
    data, error = _call_ai_service('/api/weekly/enhance', payload)
    if error is not None:
        return None, error
    if data.get('user_id') not in (None, request.user.id):
        return None, Response(
            _ai_error(
                'SESSION_EXPIRED',
                'This chat session could not be recovered.',
                SESSION_EXPIRED_RECOMMENDATIONS
            ),
            status=status.HTTP_409_CONFLICT
        )

    new_session_id = data.get('session_id') or ''
    if new_session_id:
        chat.session_id = new_session_id
        chat.save()
        cache.set(_session_owner_cache_key(new_session_id), request.user.id, 60 * 60 * 3)
    return data, None


def _save_enhanced_report(request, weekly_report, enhanced_data):
    """Save AI enhanced data with the existing transform + serializer logic.

    Returns (saved_report, None) or (None, errors).
    """
    viewset = _ai_viewset(request)
    transformed_data = viewset._transform_enhanced_data(enhanced_data, weekly_report)
    serializer = WeeklyReportCreateSerializer(
        weekly_report,
        data=transformed_data,
        partial=True,
        context={'request': request}
    )
    if not serializer.is_valid():
        print(f"❌ Enhanced report validation errors: {serializer.errors}")
        return None, serializer.errors

    saved_report = serializer.save()
    saved_report.calculate_total_hours()
    saved_report.update_completion_status()
    return saved_report, None


def _validate_week_number(raw, allow_missing=False):
    if raw in (None, ''):
        if allow_missing:
            return None, None
        return None, Response({
            'success': False,
            'message': 'week_number is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    try:
        week_number = int(raw)
    except (TypeError, ValueError):
        return None, Response({
            'success': False,
            'message': 'week_number must be a number'
        }, status=status.HTTP_400_BAD_REQUEST)
    try:
        week_dates = get_week_dates(week_number, timezone.now().year)
    except ValueError:
        return None, Response({
            'success': False,
            'message': f'Week {week_number} is not available'
        }, status=status.HTTP_404_NOT_FOUND)
    return (week_number, week_dates), None


def _build_report_payload(weekly_report, enhancement_data, additional_instructions):
    return {
        'week_number': weekly_report.week_number,
        'main_job_title': enhancement_data.get('main_job_title', ''),
        'daily_reports': enhancement_data.get('daily_reports', []),
        'operations': enhancement_data.get('operations', []),
        'user_program': enhancement_data.get('user_program', ''),
        'company_name': enhancement_data.get('company_name', ''),
        'additional_instructions': additional_instructions
    }


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def weekly_ai_enhance(request):
    """Start or resume an AI enhancement session for the current user's report."""
    week, error = _validate_week_number(request.data.get('week_number'))
    if error is not None:
        return error
    week_number, week_dates = week
    restart = bool(request.data.get('restart'))

    # An empty week has no report yet - create it so the chat can build it.
    weekly_report, _created = WeeklyReport.objects.get_or_create(
        student=request.user,
        week_number=week_number,
        defaults={'start_date': week_dates['start_date'], 'end_date': week_dates['end_date']}
    )

    chat = _get_chat_session(request.user, week_number)
    if chat and chat.status == AiChatSession.STATUS_COMPLETE and not restart:
        # The report was enhanced before - show the old chat instead of starting over.
        return Response({
            'success': True,
            'already_enhanced': True,
            'is_complete': True,
            'session_id': chat.session_id or None,
            'message': (
                f'Week {week_number} was already enhanced on '
                f'{chat.updated_at.strftime("%d %b %Y, %H:%M")}. '
                'Start a new session to keep improving it.'
            ),
            'recommendations': [
                'Choose "Improve further" to keep refining the report.',
                'Or export it as-is when you are happy with it.',
            ],
            'enhanced_at': chat.updated_at.isoformat()
        })

    viewset = _ai_viewset(request)
    enhancement_data = viewset._prepare_enhancement_data(weekly_report)
    additional_instructions = request.data.get('additional_instructions', '')
    if not OriginalUserInputs.objects.filter(weekly_report=weekly_report).exists():
        # Snapshot the untouched inputs the very first time only.
        viewset._save_original_inputs(weekly_report, enhancement_data, additional_instructions)

    resume = bool(
        chat and chat.session_id and not restart and _ai_session_alive(chat.session_id)
    )
    # report_data is sent on EVERY start (including resumes): the AI service
    # refreshes its session snapshot with it, so a session opened before the
    # student filled in the week no longer keeps showing an empty report.
    report_payload = _build_report_payload(
        weekly_report, enhancement_data, additional_instructions
    )
    payload = {
        'user_id': request.user.id,
        'mode': 'converse',
        'report_data': report_payload
    }
    if resume:
        payload['session_id'] = chat.session_id
    elif not restart:
        # Replay what was already said so the AI remembers this week's chat.
        # A deliberate restart skips the replay: the new session starts fresh,
        # with the old conversation kept in the UI behind a NEW SESSION divider.
        payload['conversation_history'] = _chat_transcript(chat)

    data, error = _call_ai_service('/api/weekly/enhance', payload)
    if error is not None and resume:
        # The AI service lost the session (restart) - start a fresh one.
        resume = False
        payload = {
            'user_id': request.user.id,
            'mode': 'converse',
            'report_data': report_payload,
            'conversation_history': _chat_transcript(chat)
        }
        data, error = _call_ai_service('/api/weekly/enhance', payload)
    if error is not None:
        return error

    session_id = data.get('session_id') or ''
    if session_id:
        # Remember who owns the session so answers can be checked up front.
        cache.set(_session_owner_cache_key(session_id), request.user.id, 60 * 60 * 3)

    if chat is None:
        # get_or_create keeps a double-clicked "Enhance" button from 500ing.
        chat, chat_created = AiChatSession.objects.get_or_create(
            student=request.user, week_number=week_number,
            defaults={'session_id': session_id}
        )
        if not chat_created and not chat.session_id and session_id:
            chat.session_id = session_id
            chat.save()
    elif not resume:
        chat.session_id = session_id
        chat.status = AiChatSession.STATUS_IN_PROGRESS
        chat.save()

    if restart and chat is not None and chat.messages.exists():
        # A restart keeps the old conversation on screen but clearly marks
        # where the fresh session begins.
        last_message = chat.messages.order_by('-created_at').first()
        if last_message is None or last_message.message_type != 'separator':
            _save_chat_message(
                chat, AiChatMessage.ROLE_ASSISTANT, NEW_SESSION_SEPARATOR,
                message_type='separator'
            )

    is_complete = bool(data.get('is_complete'))
    ready = bool(data.get('ready_to_enhance'))
    ai_message = data.get('ai_message')
    question = data.get('question')
    suggestions = data.get('suggestions') or None
    content = _assistant_content(ai_message, question)

    response_payload = {
        'success': True,
        'session_id': session_id,
        'is_complete': is_complete,
        'ready_to_enhance': ready,
        'already_enhanced': False,
        'ai_message': ai_message,
        'question': question,
        'suggestions': suggestions
    }

    if is_complete and data.get('enhanced_data'):
        # Direct mode can still finish in one shot - save it right away.
        saved_report, errors = _save_enhanced_report(
            request, weekly_report, data['enhanced_data']
        )
        if saved_report is None:
            return Response({
                'success': False,
                'message': 'The enhanced report could not be saved.',
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)
        saved_report.is_ai_enhanced = True
        saved_report.save(update_fields=['is_ai_enhanced'])
        _clear_pending(chat)
        message = _save_chat_message(
            chat, AiChatMessage.ROLE_ASSISTANT, content,
            message_type='complete',
            meta={
                'ai_message': ai_message,
                'question': question,
                'enhanced_data': data['enhanced_data']
            }
        )
        chat.status = AiChatSession.STATUS_COMPLETE
        chat.save()
        response_payload['enhanced_data'] = data['enhanced_data']
        response_payload['data'] = WeeklyReportSerializer(saved_report).data
        response_payload['message_id'] = message.id
        return Response(response_payload)

    last = chat.messages.filter(
        role=AiChatMessage.ROLE_ASSISTANT
    ).order_by('-created_at').first()
    if resume and last and last.is_pending and last.content == content:
        # Replaying the question already stored in the chat history.
        response_payload['message_id'] = last.id
        response_payload['replay'] = True
    else:
        _clear_pending(chat)
        message = _save_chat_message(
            chat, AiChatMessage.ROLE_ASSISTANT, content,
            message_type='ready' if ready else 'question',
            meta={'ai_message': ai_message, 'question': question, 'suggestions': suggestions},
            pending=True
        )
        response_payload['message_id'] = message.id
        response_payload['replay'] = False

    return Response(response_payload)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def weekly_ai_answer(request):
    """Send the user's answer (or the enhance confirmation) to the AI service."""
    session_id = request.data.get('session_id')
    answer = request.data.get('answer')
    confirm = bool(request.data.get('confirm'))

    if not session_id or not isinstance(session_id, str):
        return Response({
            'success': False,
            'message': 'session_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    if not confirm and (not answer or not str(answer).strip()):
        return Response({
            'success': False,
            'message': 'answer is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Only the user who started the session may continue it.
    chat = AiChatSession.objects.filter(
        session_id=session_id, student=request.user
    ).first()
    if chat is None:
        return Response(
            _ai_error(
                'SESSION_NOT_FOUND',
                'Session not found. Please start a new enhancement.',
                SESSION_EXPIRED_RECOMMENDATIONS
            ),
            status=status.HTTP_404_NOT_FOUND
        )
    if chat.status == AiChatSession.STATUS_COMPLETE:
        return Response({
            'success': True,
            'already_enhanced': True,
            'is_complete': True,
            'session_id': session_id,
            'message': 'This report has already been enhanced.'
        })

    user_content = 'Enhance report' if confirm else str(answer).strip()

    # Send the CURRENT report along with every answer so the AI service can
    # refresh its session snapshot - the student may have saved daily entries
    # after the session was opened.
    answer_payload = {'session_id': session_id, 'answer': user_content, 'confirm': confirm}
    weekly_report = WeeklyReport.objects.filter(
        student=request.user, week_number=chat.week_number
    ).first()
    if weekly_report is not None:
        viewset = _ai_viewset(request)
        enhancement_data = viewset._prepare_enhancement_data(weekly_report)
        original_inputs = OriginalUserInputs.objects.filter(
            weekly_report=weekly_report
        ).first()
        answer_payload['report_data'] = _build_report_payload(
            weekly_report,
            enhancement_data,
            (original_inputs.enhancement_instructions if original_inputs else '') or ''
        )

    data, error = _call_ai_service('/api/weekly/answer', answer_payload)
    if error is not None and _is_session_expired(error):
        # The service lost the session (restart/TTL) - rebuild it from the
        # stored transcript and replay this answer so nobody gets stuck.
        data, error = _recover_answer_session(request, chat, user_content)
    if error is not None:
        return error

    # The session belongs to the user who started it.
    if data.get('user_id') not in (None, request.user.id):
        return Response(
            _ai_error(
                'SESSION_NOT_FOUND',
                'Session not found. Please start a new enhancement.',
                SESSION_EXPIRED_RECOMMENDATIONS
            ),
            status=status.HTTP_404_NOT_FOUND
        )

    is_complete = bool(data.get('is_complete'))
    ready = bool(data.get('ready_to_enhance'))
    ai_message = data.get('ai_message')
    question = data.get('question')
    suggestions = data.get('suggestions') or None
    content = _assistant_content(ai_message, question)
    response_payload = {
        'success': True,
        'session_id': data.get('session_id') or session_id,
        'is_complete': is_complete,
        'ready_to_enhance': ready,
        'already_enhanced': False,
        'ai_message': ai_message,
        'question': question,
        'suggestions': suggestions
    }

    if not is_complete:
        _clear_pending(chat)
        _save_chat_message(chat, AiChatMessage.ROLE_USER, user_content)
        message = _save_chat_message(
            chat, AiChatMessage.ROLE_ASSISTANT, content,
            message_type='ready' if ready else 'question',
            meta={'ai_message': ai_message, 'question': question, 'suggestions': suggestions},
            pending=True
        )
        chat.save()  # refresh updated_at for the history view
        response_payload['message_id'] = message.id
        return Response(response_payload)

    enhanced_data = data.get('enhanced_data')
    if not enhanced_data:
        return Response({
            'success': False,
            'message': 'The AI service finished without a report. Please try again.'
        }, status=status.HTTP_502_BAD_GATEWAY)

    week_number = data.get('week_number') or chat.week_number
    weekly_report = WeeklyReport.objects.filter(
        student=request.user, week_number=week_number
    ).first()
    if weekly_report is None:
        week_dates = get_week_dates(week_number, timezone.now().year)
        weekly_report = WeeklyReport.objects.create(
            student=request.user,
            week_number=week_number,
            start_date=week_dates['start_date'],
            end_date=week_dates['end_date']
        )

    saved_report, errors = _save_enhanced_report(request, weekly_report, enhanced_data)
    if saved_report is None:
        return Response({
            'success': False,
            'message': 'The enhanced report could not be saved.',
            'errors': errors
        }, status=status.HTTP_400_BAD_REQUEST)

    saved_report.is_ai_enhanced = True
    saved_report.save(update_fields=['is_ai_enhanced'])

    _clear_pending(chat)
    _save_chat_message(chat, AiChatMessage.ROLE_USER, user_content)
    message = _save_chat_message(
        chat, AiChatMessage.ROLE_ASSISTANT, content,
        message_type='complete',
        meta={
            'ai_message': ai_message,
            'question': question,
            'enhanced_data': enhanced_data
        }
    )
    chat.status = AiChatSession.STATUS_COMPLETE
    chat.save()

    response_payload.update({
        'message_id': message.id,
        'message': 'Weekly report enhanced and saved successfully',
        'enhanced_data': enhanced_data,
        'data': WeeklyReportSerializer(saved_report).data
    })
    return Response(response_payload)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def weekly_ai_history(request):
    """Everything the assistant said about this week, so the chat can scroll back."""
    week, error = _validate_week_number(request.query_params.get('week_number'))
    if error is not None:
        return error
    week_number, _week_dates = week

    chat = _get_chat_session(request.user, week_number)
    if chat is None:
        return Response({
            'success': True,
            'session': None,
            'messages': [],
            'pending': False,
            'already_enhanced': False
        })

    messages = [
        {
            'id': message.id,
            'role': message.role,
            'content': message.content,
            'message_type': message.message_type,
            'is_pending': message.is_pending,
            'meta': message.meta or {},
            'created_at': message.created_at.isoformat()
        }
        for message in chat.messages.all()
    ]

    return Response({
        'success': True,
        'session': {
            'id': chat.id,
            'session_id': chat.session_id,
            'status': chat.status,
            'week_number': chat.week_number,
            'created_at': chat.created_at.isoformat(),
            'updated_at': chat.updated_at.isoformat()
        },
        'messages': messages,
        'pending': any(m['is_pending'] for m in messages if m['role'] == 'assistant'),
        'already_enhanced': chat.status == AiChatSession.STATUS_COMPLETE
    })