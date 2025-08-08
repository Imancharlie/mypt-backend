from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api_views

app_name = 'admin_dashboard'

# API Router
router = DefaultRouter()
router.register(r'token-usage', api_views.TokenUsageViewSet)
router.register(r'user-actions', api_views.UserActionViewSet)
router.register(r'system-metrics', api_views.SystemMetricsViewSet)

urlpatterns = [
    # Dashboard Views
    path('', views.admin_dashboard, name='dashboard'),
    path('users/', views.user_management, name='user_management'),
    path('tokens/', views.token_analytics, name='token_analytics'),
    path('reports/', views.report_analytics, name='report_analytics'),
    
    # API Endpoints
    path('api/', include([
        path('dashboard/stats/', api_views.dashboard_stats, name='api_dashboard_stats'),
        path('users/', api_views.user_management_api, name='api_user_management'),
        path('users/actions/', api_views.user_actions, name='api_user_actions'),
        path('tokens/analytics/', api_views.token_analytics_api, name='api_token_analytics'),
        path('reports/analytics/', api_views.report_analytics_api, name='api_report_analytics'),
        path('recent-activity/', api_views.recent_activity, name='api_recent_activity'),
        path('', include(router.urls)),
    ])),
] 