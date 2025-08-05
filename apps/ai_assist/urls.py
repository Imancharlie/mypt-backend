from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    path('enhance/text/', views.enhance_text, name='enhance-text'),
    path('enhance/daily/', views.enhance_daily_report, name='enhance-daily'),
    path('enhance/weekly/', views.enhance_weekly_report, name='enhance-weekly'),
    path('enhance/general/', views.enhance_general_report, name='enhance-general'),
    path('generate/summary/', views.generate_weekly_summary, name='generate-summary'),
    path('suggest/improvements/', views.suggest_improvements, name='suggest-improvements'),
    path('usage/', views.usage_stats, name='usage-stats'),
] 