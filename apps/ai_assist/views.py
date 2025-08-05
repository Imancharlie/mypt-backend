from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .services import AIService
from apps.reports.models import DailyReport
from django.db import models


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enhance_text(request):
    text = request.data.get('text', '')
    enhancement_type = request.data.get('type', 'improve')
    
    if not text:
        return Response({
            'success': False,
            'message': 'Text is required'
        }, status=400)
    
    ai_service = AIService()
    result = ai_service.enhance_text(text, enhancement_type, request.user)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enhance_daily_report(request):
    """Enhance daily report content"""
    daily_report_id = request.data.get('daily_report_id')
    field = request.data.get('field', 'description')  # description, skills_learned, etc.
    enhancement_type = request.data.get('type', 'improve')
    
    try:
        daily_report = DailyReport.objects.get(id=daily_report_id, student=request.user)
    except DailyReport.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Daily report not found'
        }, status=404)
    
    text = getattr(daily_report, field, '')
    if not text:
        return Response({
            'success': False,
            'message': f'No content found in {field} field'
        }, status=400)
    
    ai_service = AIService()
    result = ai_service.enhance_text(text, enhancement_type, request.user)
    
    if result['success']:
        # Update the field with enhanced text
        setattr(daily_report, field, result['enhanced_text'])
        daily_report.save()
        result['message'] = f'{field} enhanced successfully'
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enhance_weekly_report(request):
    """Enhance weekly report content"""
    weekly_report_id = request.data.get('weekly_report_id')
    field = request.data.get('field', 'summary')
    enhancement_type = request.data.get('type', 'improve')
    
    from apps.reports.models import WeeklyReport
    
    try:
        weekly_report = WeeklyReport.objects.get(id=weekly_report_id, student=request.user)
    except WeeklyReport.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Weekly report not found'
        }, status=404)
    
    text = getattr(weekly_report, field, '')
    if not text:
        return Response({
            'success': False,
            'message': f'No content found in {field} field'
        }, status=400)
    
    ai_service = AIService()
    result = ai_service.enhance_text(text, enhancement_type, request.user)
    
    if result['success']:
        # Update the field with enhanced text
        setattr(weekly_report, field, result['enhanced_text'])
        weekly_report.is_ai_enhanced = True
        weekly_report.save()
        result['message'] = f'{field} enhanced successfully'
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enhance_general_report(request):
    """Enhance general report content"""
    field = request.data.get('field', 'introduction')
    enhancement_type = request.data.get('type', 'improve')
    
    from apps.reports.models import GeneralReport
    
    try:
        general_report = GeneralReport.objects.get(user=request.user)
    except GeneralReport.DoesNotExist:
        return Response({
            'success': False,
            'message': 'General report not found'
        }, status=404)
    
    text = getattr(general_report, field, '')
    if not text:
        return Response({
            'success': False,
            'message': f'No content found in {field} field'
        }, status=400)
    
    ai_service = AIService()
    result = ai_service.enhance_text(text, enhancement_type, request.user)
    
    if result['success']:
        # Update the field with enhanced text
        setattr(general_report, field, result['enhanced_text'])
        general_report.is_ai_enhanced = True
        general_report.save()
        result['message'] = f'{field} enhanced successfully'
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_weekly_summary(request):
    """Generate weekly summary from daily reports"""
    week_number = request.data.get('week_number')
    
    if not week_number:
        return Response({
            'success': False,
            'message': 'Week number is required'
        }, status=400)
    
    daily_reports = DailyReport.objects.filter(
        student=request.user,
        week_number=week_number,
        is_submitted=True
    )
    
    if daily_reports.count() < 3:
        return Response({
            'success': False,
            'message': 'At least 3 daily reports required for summary generation'
        }, status=400)
    
    ai_service = AIService()
    result = ai_service.generate_weekly_summary(daily_reports, request.user)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def suggest_improvements(request):
    """Suggest improvements for reports"""
    report_text = request.data.get('text', '')
    report_type = request.data.get('type', 'general')
    
    if not report_text:
        return Response({
            'success': False,
            'message': 'Text is required'
        }, status=400)
    
    ai_service = AIService()
    result = ai_service.suggest_improvements(report_text, report_type)
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usage_stats(request):
    """Get AI usage statistics for the user"""
    from apps.reports.models import AIEnhancementLog
    
    logs = AIEnhancementLog.objects.filter(user=request.user)
    
    total_enhancements = logs.count()
    total_tokens = logs.aggregate(total=models.Sum('tokens_consumed'))['total'] or 0
    
    enhancement_types = logs.values('enhancement_type').annotate(
        count=models.Count('id')
    ).order_by('-count')
    
    content_types = logs.values('content_type').annotate(
        count=models.Count('id')
    ).order_by('-count')
    
    return Response({
        'success': True,
        'data': {
            'total_enhancements': total_enhancements,
            'total_tokens': total_tokens,
            'enhancement_types': list(enhancement_types),
            'content_types': list(content_types),
            'recent_enhancements': list(logs.order_by('-created_at')[:10].values(
                'content_type', 'enhancement_type', 'tokens_consumed', 'created_at'
            ))
        }
    }) 