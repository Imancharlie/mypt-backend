from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.reports.models import DailyReport, GeneralReport, WeeklyReport
from apps.users.models import UserProfile
from billings.models import UserBalance

from . import views as exporter_views


class ExportTokenDeductionTests(TestCase):
    """Normal exports cost 100 tokens, AI-enhanced exports cost 200 tokens."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='student1', password='pass1234')
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.student_id = 'PT-001'
        self.profile.program = 'MECHANICAL'
        self.profile.save()

        # billings.signals creates a UserBalance for every new user
        self.balance = UserBalance.objects.get(user=self.user)
        self.balance.available_tokens = 500
        self.balance.save()

    # ------------------------------------------------------------------ data

    def _weekly(self, week_number, enhanced=False):
        start = date(2026, 1, 5) + timedelta(weeks=week_number - 1)
        return WeeklyReport.objects.create(
            student=self.user,
            week_number=week_number,
            start_date=start,
            end_date=start + timedelta(days=4),
            is_ai_enhanced=enhanced,
        )

    def _daily(self):
        return DailyReport.objects.create(
            student=self.user,
            week_number=1,
            date=date(2026, 1, 5),
            description='Work done',
            hours_spent=8,
        )

    def _tokens(self):
        self.balance.refresh_from_db()
        return self.balance.available_tokens

    # --------------------------------------------------------------- helpers

    def _get(self, view, *args):
        request = self.factory.get('/api/export/')
        force_authenticate(request, user=self.user)
        return view(request, *args)

    def _post(self, view, data):
        request = self.factory.post('/api/export/', data, format='json')
        force_authenticate(request, user=self.user)
        return view(request)

    # ---------------------------------------------------- weekly deductions

    @patch('apps.exporter.views.export_weekly_report_pdf', return_value=b'%PDF-fake')
    def test_weekly_pdf_normal_costs_100(self, mock_pdf):
        report = self._weekly(1, enhanced=False)
        response = self._get(exporter_views.export_weekly_report_pdf_view, report.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._tokens(), 400)

    @patch('apps.exporter.views.export_weekly_report_pdf', return_value=b'%PDF-fake')
    def test_weekly_pdf_enhanced_costs_200(self, mock_pdf):
        report = self._weekly(1, enhanced=True)
        response = self._get(exporter_views.export_weekly_report_pdf_view, report.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._tokens(), 300)

    @patch('apps.exporter.views.export_weekly_report_docx', return_value=b'PK-fake')
    def test_weekly_docx_enhanced_costs_200(self, mock_docx):
        report = self._weekly(1, enhanced=True)
        response = self._get(exporter_views.export_weekly_report_docx_view, report.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._tokens(), 300)

    @patch('apps.exporter.views.export_weekly_report_pdf', return_value=b'%PDF-fake')
    def test_weekly_pdf_insufficient_tokens_shows_cost(self, mock_pdf):
        self.balance.available_tokens = 150
        self.balance.save()
        report = self._weekly(1, enhanced=True)

        response = self._get(exporter_views.export_weekly_report_pdf_view, report.id)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.data['requires_tokens'])
        self.assertEqual(response.data['token_cost'], 200)
        self.assertIn('200 tokens', response.data['message'])
        self.assertEqual(self._tokens(), 150)
        mock_pdf.assert_not_called()

    @patch('apps.exporter.views.export_weekly_report_pdf', side_effect=RuntimeError('boom'))
    def test_weekly_pdf_failed_generation_does_not_deduct(self, mock_pdf):
        report = self._weekly(1, enhanced=False)
        response = self._get(exporter_views.export_weekly_report_pdf_view, report.id)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self._tokens(), 500)

    # ----------------------------------------------------- daily deductions

    @patch('django.template.loader.render_to_string', return_value='<html></html>')
    def test_daily_pdf_costs_100(self, mock_render):
        report = self._daily()
        with patch.dict('sys.modules', {'weasyprint': MagicMock()}):
            response = self._get(exporter_views.export_daily_report_pdf, report.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._tokens(), 400)

    def test_daily_docx_costs_100(self):
        report = self._daily()
        response = self._get(exporter_views.export_daily_report_docx, report.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._tokens(), 400)

    def test_daily_pdf_insufficient_tokens_shows_cost(self):
        self.balance.available_tokens = 50
        self.balance.save()
        report = self._daily()

        with patch('sys.modules', {'weasyprint': MagicMock()}):
            response = self._get(exporter_views.export_daily_report_pdf, report.id)

        self.assertEqual(response.status_code, 403)
        self.assertIn('100 tokens', response.data['message'])
        self.assertEqual(self._tokens(), 50)

    # -------------------------------------------------- general deductions

    @patch('apps.exporter.views.export_general_report_pdf', return_value=b'%PDF-fake')
    def test_general_pdf_costs_100(self, mock_pdf):
        GeneralReport.objects.create(user=self.user)
        response = self._get(exporter_views.export_general_report_pdf_view)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._tokens(), 400)

    @patch('apps.exporter.views.export_general_report_pdf', return_value=b'%PDF-fake')
    def test_general_pdf_enhanced_costs_200(self, mock_pdf):
        GeneralReport.objects.create(user=self.user, is_ai_enhanced=True)
        response = self._get(exporter_views.export_general_report_pdf_view)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._tokens(), 300)

    @patch('apps.exporter.views.export_general_report_docx', return_value=b'PK-fake')
    def test_general_docx_costs_100(self, mock_docx):
        GeneralReport.objects.create(user=self.user)
        response = self._get(exporter_views.export_general_report_docx_view)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._tokens(), 400)

    # ------------------------------------------------------- bulk and logbook

    @patch('apps.exporter.views.export_weekly_report_pdf', return_value=b'%PDF-fake')
    def test_bulk_weekly_export_costs_100(self, mock_pdf):
        report = self._weekly(1, enhanced=False)
        response = self._post(
            exporter_views.bulk_export,
            {'report_ids': [report.id], 'type': 'pdf', 'report_type': 'weekly'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._tokens(), 400)

    @patch('apps.exporter.services.export_all_weekly_reports_pdf', return_value=b'%PDF-fake')
    def test_logbook_all_normal_costs_100_each(self, mock_pdf):
        for week in range(1, 5):
            self._weekly(week, enhanced=False)
        response = self._post(
            exporter_views.export_all_weekly_reports,
            {'type': 'pdf', 'force_export': True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._tokens(), 100)  # 500 - 4 * 100

    @patch('apps.exporter.services.export_all_weekly_reports_pdf', return_value=b'%PDF-fake')
    def test_logbook_all_enhanced_costs_200_each(self, mock_pdf):
        for week in range(1, 5):
            self._weekly(week, enhanced=True)
        self.balance.available_tokens = 1000
        self.balance.save()

        response = self._post(
            exporter_views.export_all_weekly_reports,
            {'type': 'pdf', 'force_export': True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._tokens(), 200)  # 1000 - 4 * 200

    @patch('apps.exporter.services.export_all_weekly_reports_pdf', return_value=b'%PDF-fake')
    def test_logbook_mixed_costs_sum_individual_reports(self, mock_pdf):
        for week in range(1, 4):
            self._weekly(week, enhanced=False)
        for week in range(4, 6):
            self._weekly(week, enhanced=True)
        self.balance.available_tokens = 1000
        self.balance.save()

        response = self._post(
            exporter_views.export_all_weekly_reports,
            {'type': 'pdf', 'force_export': True},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._tokens(), 300)  # 1000 - (3 * 100 + 2 * 200)

    @patch('apps.exporter.services.export_all_weekly_reports_pdf', return_value=b'%PDF-fake')
    def test_logbook_insufficient_tokens_shows_breakdown(self, mock_pdf):
        for week in range(1, 4):
            self._weekly(week, enhanced=False)
        for week in range(4, 6):
            self._weekly(week, enhanced=True)

        response = self._post(
            exporter_views.export_all_weekly_reports,
            {'type': 'pdf', 'force_export': True},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['token_cost'], 700)
        self.assertIn('3 normal + 2 enhanced', response.data['message'])
        self.assertEqual(response.data['token_breakdown'], {'normal': 3, 'enhanced': 2})
        self.assertEqual(self._tokens(), 500)
        mock_pdf.assert_not_called()
