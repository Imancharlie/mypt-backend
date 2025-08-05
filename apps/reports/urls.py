from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DailyReportViewSet, WeeklyReportViewSet, 
    MainJobViewSet, MainJobOperationViewSet,
    MainJobOperationsViewSet, MainJobDetailViewSet
)

router = DefaultRouter()
router.register(r'daily', DailyReportViewSet, basename='daily')
router.register(r'weekly', WeeklyReportViewSet, basename='weekly')
router.register(r'main-jobs', MainJobViewSet, basename='main-job')

urlpatterns = [
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
] 