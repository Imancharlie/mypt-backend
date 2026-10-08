from django.urls import path, re_path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DailyReportViewSet, WeeklyReportViewSet, 
    MainJobViewSet, MainJobOperationViewSet,
    MainJobOperationsViewSet, MainJobDetailViewSet,
    ai_fetch_report_data, ai_save_enhanced_report,
    weekly_ai_enhance, weekly_ai_answer, weekly_ai_history
)

router = DefaultRouter()
router.register(r'daily', DailyReportViewSet, basename='daily')
router.register(r'weekly', WeeklyReportViewSet, basename='weekly')
router.register(r'main-jobs', MainJobViewSet, basename='main-job')

urlpatterns = [
    # AI enhancement proxy endpoints (slash optional for the frontend client)
    re_path(r'^weekly/ai/enhance/?$', weekly_ai_enhance, name='weekly-ai-enhance'),
    re_path(r'^weekly/ai/answer/?$', weekly_ai_answer, name='weekly-ai-answer'),
    re_path(r'^weekly/ai/history/?$', weekly_ai_history, name='weekly-ai-history'),
    path('', include(router.urls)),
    # Custom endpoints for main job operations management
    path('main-jobs/<int:main_job_id>/operations/', MainJobOperationsViewSet.as_view({
        'get': 'list', 
        'post': 'create'
    }), name='main-job-operations'),
    path('main-jobs/<int:main_job_id>/operations/<int:pk>/', MainJobOperationsViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='main-job-operation-detail'),
    # Custom endpoint for updating main job title
    path('main-jobs/<int:pk>/', MainJobDetailViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update'
    }), name='main-job-detail'),
    # AI service endpoints
    path('ai/fetch-report-data/', ai_fetch_report_data, name='ai-fetch-report-data'),
    path('ai/save-enhanced-report/', ai_save_enhanced_report, name='ai-save-enhanced-report'),
] 