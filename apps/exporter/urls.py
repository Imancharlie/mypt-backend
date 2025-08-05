from django.urls import path
from . import views

app_name = 'export'

urlpatterns = [
    path('weekly/<int:weekly_report_id>/pdf/', views.export_weekly_report_pdf_view, name='weekly-pdf'),
    path('weekly/<int:weekly_report_id>/docx/', views.export_weekly_report_docx_view, name='weekly-docx'),
    path('daily/<int:daily_report_id>/pdf/', views.export_daily_report_pdf, name='daily-pdf'),
    path('daily/<int:daily_report_id>/docx/', views.export_daily_report_docx, name='daily-docx'),
    path('general/pdf/', views.export_general_report_pdf_view, name='general-pdf'),
    path('general/docx/', views.export_general_report_docx_view, name='general-docx'),
    path('bulk/', views.bulk_export, name='bulk-export'),
] 