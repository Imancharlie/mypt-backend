from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from . import views as report_views
from .models import AiChatMessage, AiChatSession, WeeklyReport

User = get_user_model()


class AiChatSessionRecoveryTests(TestCase):
    """A lost AI session must never become a dead end for the student."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='chatuser', password='pass', email='chatuser@example.com'
        )
        start = date(2026, 1, 5) + timedelta(weeks=2)
        self.report = WeeklyReport.objects.create(
            student=self.user,
            week_number=3,
            start_date=start,
            end_date=start + timedelta(days=4),
        )
        self.chat = AiChatSession.objects.create(
            student=self.user, week_number=3, session_id='old-sid'
        )
        AiChatMessage.objects.create(
            session=self.chat, role=AiChatMessage.ROLE_ASSISTANT,
            content='What did you do in week 3?', message_type='question'
        )
        AiChatMessage.objects.create(
            session=self.chat, role=AiChatMessage.ROLE_USER, content='I wired sockets'
        )

    @staticmethod
    def _expired_error():
        from rest_framework.response import Response
        return Response(
            report_views._ai_error(
                'SESSION_EXPIRED', 'This chat session has expired.',
                report_views.SESSION_EXPIRED_RECOMMENDATIONS
            ),
            status=status.HTTP_502_BAD_GATEWAY
        )

    @staticmethod
    def _viewset_mock():
        mock = MagicMock()
        mock._prepare_enhancement_data.return_value = {}
        return mock

    def _post_answer(self, answer='hello'):
        request = self.factory.post(
            '/api/reports/weekly/ai/answer',
            {'session_id': 'old-sid', 'answer': answer},
            format='json'
        )
        force_authenticate(request, user=self.user)
        return report_views.weekly_ai_answer(request)

    def test_answer_rebuilds_expired_session_and_continues(self):
        fresh = {
            'success': True,
            'session_id': 'rebuilt-sid',
            'user_id': self.user.id,
            'is_complete': False,
            'ready_to_enhance': False,
            'ai_message': 'Thanks for sharing.',
            'question': 'Which tools did you use?',
            'suggestions': None,
        }
        with patch.object(
            report_views, '_call_ai_service',
            side_effect=[(None, self._expired_error()), (fresh, None)]
        ) as mock_call, patch.object(
            report_views, '_ai_viewset', return_value=self._viewset_mock()
        ):
            response = self._post_answer('I wired sockets')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['session_id'], 'rebuilt-sid')
        self.chat.refresh_from_db()
        self.assertEqual(self.chat.session_id, 'rebuilt-sid')

        # The rebuild replays the stored transcript plus this answer.
        rebuild_payload = mock_call.call_args_list[1].args[1]
        self.assertNotIn('session_id', rebuild_payload)
        self.assertEqual(rebuild_payload['user_message'], 'I wired sockets')
        roles = [m['role'] for m in rebuild_payload['conversation_history']]
        self.assertEqual(roles, ['assistant', 'user'])

    def test_answer_recovery_failure_returns_recommendations(self):
        with patch.object(
            report_views, '_call_ai_service',
            side_effect=[(None, self._expired_error()), (None, self._expired_error())]
        ), patch.object(
            report_views, '_ai_viewset', return_value=self._viewset_mock()
        ):
            response = self._post_answer()

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data['code'], 'SESSION_EXPIRED')
        self.assertTrue(response.data['recommendations'])

    def test_answer_unknown_session_gives_next_steps(self):
        request = self.factory.post(
            '/api/reports/weekly/ai/answer',
            {'session_id': 'missing-sid', 'answer': 'hi'},
            format='json'
        )
        force_authenticate(request, user=self.user)
        response = report_views.weekly_ai_answer(request)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['code'], 'SESSION_NOT_FOUND')
        self.assertTrue(response.data['recommendations'])


class RestartEnhancementTests(TestCase):
    """'Improve further' opens a fresh session with a visible divider."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='reuser', password='pass', email='reuser@example.com'
        )
        start = date(2026, 1, 5) + timedelta(weeks=3)
        self.report = WeeklyReport.objects.create(
            student=self.user,
            week_number=4,
            start_date=start,
            end_date=start + timedelta(days=4),
        )
        self.chat = AiChatSession.objects.create(
            student=self.user, week_number=4, session_id='done-sid',
            status=AiChatSession.STATUS_COMPLETE,
        )
        AiChatMessage.objects.create(
            session=self.chat, role=AiChatMessage.ROLE_USER, content='Enhance report'
        )
        AiChatMessage.objects.create(
            session=self.chat, role=AiChatMessage.ROLE_ASSISTANT,
            content='Enhancement completed!', message_type='complete'
        )

    def test_restart_starts_fresh_and_writes_separator(self):
        captured = {}

        def fake_call(path, payload):
            captured['path'] = path
            captured['payload'] = payload
            return {
                'success': True,
                'session_id': 'fresh-sid',
                'is_complete': False,
                'ready_to_enhance': False,
                'ai_message': 'Starting over.',
                'question': 'Tell me about week 4.',
                'suggestions': None,
            }, None

        mock_viewset = MagicMock()
        mock_viewset._prepare_enhancement_data.return_value = {}

        request = self.factory.post(
            '/api/reports/weekly/ai/enhance',
            {'week_number': 4, 'restart': True},
            format='json'
        )
        force_authenticate(request, user=self.user)
        with patch.object(report_views, '_call_ai_service', side_effect=fake_call), \
                patch.object(report_views, '_ai_viewset', return_value=mock_viewset):
            response = report_views.weekly_ai_enhance(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        # A deliberate restart starts the AI fresh - no transcript replay.
        self.assertNotIn('conversation_history', captured['payload'])
        self.assertNotIn('session_id', captured['payload'])

        self.chat.refresh_from_db()
        self.assertEqual(self.chat.session_id, 'fresh-sid')
        self.assertEqual(self.chat.status, AiChatSession.STATUS_IN_PROGRESS)

        kinds = list(
            self.chat.messages.order_by('created_at').values_list(
                'message_type', flat=True
            )
        )
        self.assertIn('separator', kinds)
        self.assertEqual(kinds[-2], 'separator')
        self.assertEqual(kinds[-1], 'question')

    def test_separator_is_not_replayed_to_the_ai(self):
        AiChatMessage.objects.create(
            session=self.chat, role=AiChatMessage.ROLE_ASSISTANT,
            content=report_views.NEW_SESSION_SEPARATOR, message_type='separator'
        )
        transcript = report_views._chat_transcript(self.chat)
        self.assertNotIn(
            report_views.NEW_SESSION_SEPARATOR,
            [m['content'] for m in transcript]
        )
        self.assertEqual(len(transcript), 2)


class AiServiceErrorMappingTests(TestCase):
    """Failures are classified so the UI can offer the right next step."""

    @staticmethod
    def _response(status_code, body):
        mock = MagicMock(status_code=status_code)
        mock.json.return_value = body
        return mock

    def test_invalid_session_maps_to_expired_code(self):
        with patch.object(
            report_views.requests, 'post',
            return_value=self._response(200, {'success': False, 'error': 'Invalid session ID'})
        ):
            data, error = report_views._call_ai_service('/api/weekly/answer', {})

        self.assertIsNone(data)
        self.assertEqual(error.data['code'], 'SESSION_EXPIRED')
        self.assertTrue(error.data['recommendations'])

    def test_timeout_maps_to_timeout_code(self):
        with patch.object(
            report_views.requests, 'post',
            side_effect=report_views.requests.exceptions.Timeout
        ):
            data, error = report_views._call_ai_service('/api/weekly/answer', {})

        self.assertIsNone(data)
        self.assertEqual(error.data['code'], 'AI_TIMEOUT')
        self.assertEqual(error.status_code, status.HTTP_504_GATEWAY_TIMEOUT)

    def test_service_down_maps_to_unavailable_code(self):
        with patch.object(
            report_views.requests, 'post',
            side_effect=report_views.requests.exceptions.ConnectionError
        ):
            data, error = report_views._call_ai_service('/api/weekly/answer', {})

        self.assertIsNone(data)
        self.assertEqual(error.data['code'], 'AI_UNAVAILABLE')
        self.assertTrue(error.data['recommendations'])

    def test_other_service_errors_keep_service_message(self):
        with patch.object(
            report_views.requests, 'post',
            return_value=self._response(
                200, {'success': False, 'error': 'The report is not ready to enhance yet.'}
            )
        ):
            data, error = report_views._call_ai_service('/api/weekly/answer', {})

        self.assertIsNone(data)
        self.assertEqual(error.data['code'], 'AI_ENHANCE_FAILED')
        self.assertIn('not ready', error.data['message'])
