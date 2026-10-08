from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .services import export_weekly_report_pdf, export_weekly_report_docx, export_general_report_pdf, export_general_report_docx
from .diagram_client import MyPTMediaClient
from apps.reports.models import WeeklyReport, GeneralReport, DailyReport
from apps.core.permissions import IsOwnerOrReadOnly
from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)

# Token costs per export (1 token = 2 TSH)
NORMAL_EXPORT_TOKEN_COST = 100    # 200 TSH
ENHANCED_EXPORT_TOKEN_COST = 200  # 400 TSH


def _export_token_cost(report):
    """Normal reports cost 100 tokens, AI-enhanced reports cost 200 tokens."""
    if getattr(report, 'is_ai_enhanced', False):
        return ENHANCED_EXPORT_TOKEN_COST
    return NORMAL_EXPORT_TOKEN_COST


def _check_export_tokens(user, token_cost):
    """Check the user can afford an export.

    Returns None when the export may proceed, otherwise a 403 Response
    describing the required cost.
    """
    try:
        from billings.models import UserBalance
        user_balance = UserBalance.objects.get(user=user)
    except UserBalance.DoesNotExist:
        return None  # No balance record - proceed with export

    available = user_balance.available_tokens
    if available >= token_cost:
        return None

    if available <= 0:
        # Send SMS notification for zero token export attempt
        try:
            from apps.users.sms_service import send_zero_token_sms
            user_name = user.get_full_name() or user.username
            send_zero_token_sms(user.email, user_name)
        except Exception as e:
            logger.error(f"Failed to send zero token SMS: {str(e)}")

    return Response({
        'success': False,
        'message': (
            f'This export costs {token_cost} tokens. You currently have '
            f'{available} tokens. Visit the billing page to get more tokens.'
        ),
        'token_cost': token_cost,
        'available_tokens': available,
        'requires_tokens': True
    }, status=403)


def _deduct_export_tokens(user, token_cost):
    """Deduct the export cost after the export was generated successfully."""
    try:
        from billings.models import UserBalance
        user_balance = UserBalance.objects.get(user=user)
    except UserBalance.DoesNotExist:
        logger.warning(f"No user balance found for user {user.username}")
        return False

    if user_balance.deduct_tokens(token_cost):
        logger.info(f"Deducted {token_cost} tokens from user {user.username}")
        return True

    logger.warning(
        f"Could not deduct {token_cost} tokens from user {user.username}: "
        f"balance {user_balance.available_tokens}"
    )
    return False


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_weekly_report_pdf_view(request, weekly_report_id):
    """Export weekly report as PDF"""
    try:
        weekly_report = WeeklyReport.objects.get(id=weekly_report_id, student=request.user)
    except WeeklyReport.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Weekly report not found'
        }, status=404)

    # Check user's token balance (enhanced reports cost more)
    token_cost = _export_token_cost(weekly_report)
    denied = _check_export_tokens(request.user, token_cost)
    if denied is not None:
        return denied

    try:
        pdf_content = export_weekly_report_pdf(weekly_report)
        _deduct_export_tokens(request.user, token_cost)
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="weekly_report_{weekly_report.week_number}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Error generating PDF for weekly report {weekly_report_id}: {str(e)}")
        return Response({
            'success': False,
            'message': 'Unable to generate PDF report. Please try again or contact support if the issue persists.'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_weekly_report_docx_view(request, weekly_report_id):
    """Export weekly report as DOCX"""
    try:
        weekly_report = WeeklyReport.objects.get(id=weekly_report_id, student=request.user)
    except WeeklyReport.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Weekly report not found'
        }, status=404)

    # Check user's token balance (enhanced reports cost more)
    token_cost = _export_token_cost(weekly_report)
    denied = _check_export_tokens(request.user, token_cost)
    if denied is not None:
        return denied

    try:
        docx_content = export_weekly_report_docx(weekly_report)
        _deduct_export_tokens(request.user, token_cost)
        response = HttpResponse(docx_content, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="weekly_report_{weekly_report.week_number}.docx"'
        return response
    except Exception as e:
        logger.error(f"Error generating DOCX for weekly report {weekly_report_id}: {str(e)}")
        return Response({
            'success': False,
            'message': 'Unable to generate DOCX report. Please try again or contact support if the issue persists.'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_daily_report_pdf(request, daily_report_id):
    """Export daily report as PDF"""
    try:
        daily_report = DailyReport.objects.get(id=daily_report_id, student=request.user)
    except DailyReport.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Daily report not found'
        }, status=404)

    # Check user's token balance
    token_cost = _export_token_cost(daily_report)
    denied = _check_export_tokens(request.user, token_cost)
    if denied is not None:
        return denied

    # For daily reports, we'll create a simple PDF
    from django.template.loader import render_to_string
    from weasyprint import HTML, CSS
    from io import BytesIO
    from django.http import HttpResponse
    from django.utils import timezone
    
    context = {
        'report': daily_report,
        'student': daily_report.student,
        'profile': daily_report.student.profile,
        'company': daily_report.student.profile.company_name,
        'export_date': timezone.now().strftime('%B %d, %Y')
    }
    
    html_string = render_to_string('exports/daily_report.html', context)
    
    css_string = '''
    @page {
        size: A4;
        margin: 1in;
    }
    body {
        font-family: 'Times New Roman', serif;
        font-size: 12pt;
        line-height: 1.5;
        color: #333;
    }
    .header {
        text-align: center;
        margin-bottom: 30px;
        border-bottom: 2px solid #333;
        padding-bottom: 20px;
    }
    .section {
        margin-bottom: 25px;
    }
    .section-title {
        font-size: 14pt;
        font-weight: bold;
        color: #2c3e50;
        border-bottom: 1px solid #bdc3c7;
        padding-bottom: 5px;
        margin-bottom: 15px;
    }
    '''
    
    html = HTML(string=html_string)
    css = CSS(string=css_string)
    
    pdf_buffer = BytesIO()
    html.write_pdf(pdf_buffer, stylesheets=[css])
    pdf_buffer.seek(0)
    
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="daily_report_{daily_report.date}.pdf"'

    _deduct_export_tokens(request.user, token_cost)
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_daily_report_docx(request, daily_report_id):
    """Export daily report as DOCX"""
    try:
        daily_report = DailyReport.objects.get(id=daily_report_id, student=request.user)
    except DailyReport.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Daily report not found'
        }, status=404)

    # Check user's token balance
    token_cost = _export_token_cost(daily_report)
    denied = _check_export_tokens(request.user, token_cost)
    if denied is not None:
        return denied

    from docx import Document
    from docx.shared import Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from io import BytesIO
    from django.http import HttpResponse
    from django.utils import timezone
    
    doc = Document()
    
    # Set document margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Header
    header = doc.add_heading('DAILY TRAINING REPORT', 0)
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Student and company info
    info_table = doc.add_table(rows=5, cols=2)
    info_table.style = 'Table Grid'
    
    info_data = [
        ('Student Name:', daily_report.student.get_full_name()),
        ('Student ID:', daily_report.student.profile.student_id),
        ('Program:', daily_report.student.profile.get_program_display()),
        ('Company:', daily_report.student.profile.company_name or ''),
        ('Date:', daily_report.date.strftime('%B %d, %Y')),
    ]
    
    for i, (label, value) in enumerate(info_data):
        info_table.cell(i, 0).text = label
        info_table.cell(i, 1).text = value
    
    doc.add_paragraph()
    
    # Daily Activities
    doc.add_heading('Daily Activities', level=1)
    doc.add_paragraph(daily_report.description)
    
    # Hours Spent
    doc.add_heading('Hours Spent', level=1)
    doc.add_paragraph(f"Total hours worked: {daily_report.hours_spent}")
    
    # Skills Learned
    if getattr(daily_report, 'skills_learned', None):
        doc.add_heading('Skills Learned', level=1)
        doc.add_paragraph(daily_report.skills_learned)
    
    # Challenges Faced
    if getattr(daily_report, 'challenges_faced', None):
        doc.add_heading('Challenges Faced', level=1)
        doc.add_paragraph(daily_report.challenges_faced)
    
    # Supervisor Feedback
    if getattr(daily_report, 'supervisor_feedback', None):
        doc.add_heading('Supervisor Feedback', level=1)
        doc.add_paragraph(daily_report.supervisor_feedback)
    
    # Footer
    doc.add_paragraph()
    footer = doc.add_paragraph(f"Generated on {timezone.now().strftime('%B %d, %Y')}")
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Save to buffer
    doc_buffer = BytesIO()
    doc.save(doc_buffer)
    doc_buffer.seek(0)
    
    response = HttpResponse(doc_buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename="daily_report_{daily_report.date}.docx"'

    _deduct_export_tokens(request.user, token_cost)
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_general_report_pdf_view(request):
    """Export general report as PDF"""
    try:
        general_report = GeneralReport.objects.get(user=request.user)
    except GeneralReport.DoesNotExist:
        return Response({
            'success': False,
            'message': 'General report not found'
        }, status=404)

    # Check user's token balance (enhanced reports cost more)
    token_cost = _export_token_cost(general_report)
    denied = _check_export_tokens(request.user, token_cost)
    if denied is not None:
        return denied

    try:
        pdf_content = export_general_report_pdf(general_report)
        _deduct_export_tokens(request.user, token_cost)
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="general_report.pdf"'
        return response
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error generating PDF: {str(e)}'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_general_report_docx_view(request):
    """Export general report as DOCX"""
    try:
        general_report = GeneralReport.objects.get(user=request.user)
    except GeneralReport.DoesNotExist:
        return Response({
            'success': False,
            'message': 'General report not found'
        }, status=404)

    # Check user's token balance (enhanced reports cost more)
    token_cost = _export_token_cost(general_report)
    denied = _check_export_tokens(request.user, token_cost)
    if denied is not None:
        return denied

    try:
        docx_content = export_general_report_docx(general_report)
        _deduct_export_tokens(request.user, token_cost)
        response = HttpResponse(docx_content, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="general_report.docx"'
        return response
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error generating DOCX: {str(e)}'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_export(request):
    """Bulk export multiple reports"""
    report_ids = request.data.get('report_ids', [])
    export_type = request.data.get('type', 'pdf')  # pdf or docx
    report_type = request.data.get('report_type', 'weekly')  # daily, weekly, general

    if not report_ids:
        return Response({
            'success': False,
            'message': 'Report IDs are required'
        }, status=400)

    # This is a simplified bulk export - in a real implementation,
    # you might want to create a zip file with multiple reports
    if report_type == 'weekly':
        try:
            weekly_report = WeeklyReport.objects.get(id=report_ids[0], student=request.user)
        except WeeklyReport.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Weekly report not found'
            }, status=404)

        token_cost = _export_token_cost(weekly_report)
        denied = _check_export_tokens(request.user, token_cost)
        if denied is not None:
            return denied

        if export_type == 'pdf':
            pdf_content = export_weekly_report_pdf(weekly_report)
            _deduct_export_tokens(request.user, token_cost)
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="weekly_report_{weekly_report.week_number}.pdf"'
            return response
        else:
            docx_content = export_weekly_report_docx(weekly_report)
            _deduct_export_tokens(request.user, token_cost)
            response = HttpResponse(docx_content, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            response['Content-Disposition'] = f'attachment; filename="weekly_report_{weekly_report.week_number}.docx"'
            return response

    return Response({
        'success': False,
        'message': 'Bulk export not implemented for this report type'
    }, status=400)


class DiagramManagementAPIView(APIView):
    """API endpoint for managing diagram content for weekly reports.
    
    This acts as a proxy between the frontend and the dedicated media server,
    handling authentication and providing a unified interface for diagram operations.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, weekly_report_id):
        """GET diagram content for a weekly report."""
        try:
            weekly_report = WeeklyReport.objects.get(id=weekly_report_id, student=request.user)
        except WeeklyReport.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Weekly report not found'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            client = MyPTMediaClient()
            report_reference = str(weekly_report.id)
            diagram_data = client.get_document(report_reference)
            
            return Response({
                'success': True,
                'data': diagram_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching diagram for report {weekly_report_id}: {e}")
            return Response({
                'success': False,
                'message': 'Unable to fetch diagram content'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, weekly_report_id):
        """POST to create diagram content for a weekly report."""
        try:
            weekly_report = WeeklyReport.objects.get(id=weekly_report_id, student=request.user)
        except WeeklyReport.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Weekly report not found'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            client = MyPTMediaClient()
            report_reference = str(weekly_report.id)
            text = request.data.get('text', '')
            
            diagram_data = client.create_document(report_reference, text)
            
            return Response({
                'success': True,
                'data': diagram_data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating diagram for report {weekly_report_id}: {e}")
            return Response({
                'success': False,
                'message': 'Unable to create diagram content'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, weekly_report_id):
        """PUT to update diagram text for a weekly report."""
        try:
            weekly_report = WeeklyReport.objects.get(id=weekly_report_id, student=request.user)
        except WeeklyReport.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Weekly report not found'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            client = MyPTMediaClient()
            report_reference = str(weekly_report.id)
            text = request.data.get('text', '')
            
            diagram_data = client.save_text(report_reference, text)
            
            return Response({
                'success': True,
                'data': diagram_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error updating diagram for report {weekly_report_id}: {e}")
            return Response({
                'success': False,
                'message': 'Unable to update diagram content'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, weekly_report_id):
        """DELETE diagram content for a weekly report."""
        try:
            weekly_report = WeeklyReport.objects.get(id=weekly_report_id, student=request.user)
        except WeeklyReport.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Weekly report not found'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            client = MyPTMediaClient()
            report_reference = str(weekly_report.id)
            
            client.delete_document(report_reference)
            
            return Response({
                'success': True,
                'message': 'Diagram content deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"Error deleting diagram for report {weekly_report_id}: {e}")
            return Response({
                'success': False,
                'message': 'Unable to delete diagram content'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DiagramImageAPIView(APIView):
    """API endpoint for managing diagram images for weekly reports."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, weekly_report_id):
        """POST to upload/update diagram image for a weekly report."""
        try:
            weekly_report = WeeklyReport.objects.get(id=weekly_report_id, student=request.user)
        except WeeklyReport.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Weekly report not found'
            }, status=status.HTTP_404_NOT_FOUND)

        if 'image' not in request.FILES:
            return Response({
                'success': False,
                'message': 'No image file provided'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = MyPTMediaClient()
            report_reference = str(weekly_report.id)
            image_file = request.FILES['image']
            
            # Save uploaded file temporarily
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                for chunk in image_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            try:
                diagram_data = client.set_image(report_reference, temp_path)
                return Response({
                    'success': True,
                    'data': diagram_data
                }, status=status.HTTP_201_CREATED)
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
        except Exception as e:
            logger.error(f"Error uploading diagram image for report {weekly_report_id}: {e}")
            return Response({
                'success': False,
                'message': 'Unable to upload diagram image'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, weekly_report_id):
        """DELETE diagram image for a weekly report."""
        try:
            weekly_report = WeeklyReport.objects.get(id=weekly_report_id, student=request.user)
        except WeeklyReport.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Weekly report not found'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            client = MyPTMediaClient()
            report_reference = str(weekly_report.id)
            image_id = request.query_params.get('image_id')
            
            diagram_data = client.delete_image(report_reference, image_id)
            
            return Response({
                'success': True,
                'data': diagram_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error deleting diagram image for report {weekly_report_id}: {e}")
            return Response({
                'success': False,
                'message': 'Unable to delete diagram image'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def export_all_weekly_reports(request):
    """Export all weekly reports as a combined PDF (logbook)"""
    export_type = request.data.get('type', 'pdf')  # pdf or docx
    force_export = request.data.get('force_export', False)  # Allow override for <4 reports

    try:
        from .services import export_all_weekly_reports_pdf, export_all_weekly_reports_docx
        weekly_reports = WeeklyReport.objects.filter(student=request.user).order_by('week_number')

        if not weekly_reports.exists():
            return Response({
                'success': False,
                'message': 'No weekly reports found to export'
            }, status=404)

        report_count = weekly_reports.count()

        # Check if user has at least 4 reports (unless force_export is True)
        if report_count < 4 and not force_export:
            return Response({
                'success': False,
                'message': f'Logbook export requires at least 4 weekly reports. You currently have {report_count} report(s). Please export individual weekly reports instead.',
                'report_count': report_count,
                'requires_more_reports': True
            }, status=400)

        # Calculate token cost: 100 per normal report, 200 per AI-enhanced report
        enhanced_count = weekly_reports.filter(is_ai_enhanced=True).count()
        normal_count = report_count - enhanced_count
        token_cost = (
            normal_count * NORMAL_EXPORT_TOKEN_COST
            + enhanced_count * ENHANCED_EXPORT_TOKEN_COST
        )
        cost_breakdown = f'{normal_count} normal + {enhanced_count} enhanced'

        # Check user's token balance
        try:
            from billings.models import UserBalance
            user_balance = UserBalance.objects.get(user=request.user)
            if user_balance.available_tokens < token_cost:
                return Response({
                    'success': False,
                    'message': f'Exporting this logbook ({cost_breakdown}) costs {token_cost} tokens. You currently have {user_balance.available_tokens} tokens.',
                    'token_cost': token_cost,
                    'available_tokens': user_balance.available_tokens,
                    'token_breakdown': {
                        'normal': normal_count,
                        'enhanced': enhanced_count
                    },
                    'requires_tokens': True
                }, status=403)
        except UserBalance.DoesNotExist:
            pass  # If no balance record, proceed with export

        # Generate the export
        try:
            if export_type == 'pdf':
                pdf_content = export_all_weekly_reports_pdf(weekly_reports)
                response = HttpResponse(pdf_content, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="logbook_all_weekly_reports.pdf"'
            else:
                docx_content = export_all_weekly_reports_docx(weekly_reports)
                response = HttpResponse(docx_content, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                response['Content-Disposition'] = f'attachment; filename="logbook_all_weekly_reports.docx"'

            # Deduct tokens after successful export
            _deduct_export_tokens(request.user, token_cost)

            return response
        except Exception as export_error:
            logger.error(f"Error generating export content: {str(export_error)}")
            import traceback
            logger.error(traceback.format_exc())
            return Response({
                'success': False,
                'message': 'Unable to generate logbook content. Please check your reports and try again.'
            }, status=500)

    except Exception as e:
        logger.error(f"Error in export_all_weekly_reports: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return Response({
            'success': False,
            'message': 'Unable to generate combined logbook report. Please ensure you have enough reports and try again, or contact support if the issue persists.'
        }, status=500)
