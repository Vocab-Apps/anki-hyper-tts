#!/usr/bin/env python3
"""Unit tests for HTTP-status -> error categorization in TTS services.

These cover the mis-categorizations found during the Sentry audio-error
review (ANKI-HYPER-TTS-HHQ / HHA / HT9): cases that used to be raised as the
legacy, non-retry-aware ``RequestError`` and are now mapped to the correct
permanent / transient ``ServiceRequestError`` subclass.
"""

import unittest
import unittest.mock as mock

from hypertts_addon.services import service_azure
from hypertts_addon.services import service_google
from hypertts_addon.services import service_gemini
from hypertts_addon import logging_utils
from hypertts_addon import errors

logger = logging_utils.get_test_child_logger(__name__)


def _make_voice(options=None, voice_key=None):
    voice = mock.Mock()
    voice.name = 'Test Voice'
    voice.voice_key = voice_key if voice_key is not None else {'name': 'test-voice'}
    voice.options = options if options is not None else {}
    return voice


class TestAzureErrorMapping(unittest.TestCase):
    """service_azure.get_tts_audio HTTP-status -> error mapping."""

    def setUp(self):
        self.azure_service = service_azure.Azure()
        self.azure_service._config = {'region': 'eastus', 'api_key': 'fake_api_key'}
        with mock.patch.object(self.azure_service, 'token_refresh_required', return_value=False):
            self.azure_service.access_token = 'fake_token'
        self.voice = _make_voice(options={'rate': {'default': 1.0}, 'pitch': {'default': 0}})

    def _call(self, status_code, reason='', text='', headers=None):
        mock_response = mock.Mock()
        mock_response.status_code = status_code
        mock_response.reason = reason
        mock_response.text = text
        mock_response.headers = {} if headers is None else headers
        with mock.patch.object(self.azure_service, 'token_refresh_required', return_value=False):
            with mock.patch('requests.post', return_value=mock_response):
                return self.azure_service.get_tts_audio('Test text', self.voice, {})

    def test_429_quota_exceeded_no_retry_after_is_permanent(self):
        # ANKI-HYPER-TTS-HHA: body "Quota Exceeded", no Retry-After header.
        # The tier quota is exhausted -> permanent until upgrade / reset.
        with self.assertLogs('hypertts.service_azure', level='WARNING') as log_context:
            with self.assertRaises(errors.ServicePermissionError) as ctx:
                self._call(429, reason='Too Many Requests', text='Quota Exceeded')
        self.assertIsInstance(ctx.exception, errors.PermanentError)
        self.assertEqual(ctx.exception.retryable, False)
        self.assertIn('429', str(ctx.exception))
        self.assertIn('Quota Exceeded', str(ctx.exception))
        # still logged as a warning, not an error
        self.assertEqual(len(log_context.output), 1)
        self.assertIn('WARNING', log_context.output[0])
        self.assertIn('status code 429', log_context.output[0])

    def test_429_with_retry_after_is_retryable(self):
        with self.assertRaises(errors.RateLimitRetryAfterError) as ctx:
            self._call(429, reason='Too Many Requests', text='slow down',
                       headers={'Retry-After': '17'})
        self.assertIsInstance(ctx.exception, errors.TransientError)
        self.assertEqual(ctx.exception.retryable, True)
        self.assertEqual(ctx.exception.retry_after, 17)

    def test_429_with_unparseable_retry_after_defaults(self):
        with self.assertRaises(errors.RateLimitRetryAfterError) as ctx:
            self._call(429, headers={'Retry-After': 'Wed, 21 Oct 2026 07:28:00 GMT'})
        self.assertEqual(ctx.exception.retry_after, 60)

    def test_401_is_permission_error(self):
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            self._call(401, reason='Unauthorized')
        self.assertEqual(ctx.exception.retryable, False)

    def test_403_is_permission_error(self):
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            self._call(403, reason='Forbidden')
        self.assertEqual(ctx.exception.retryable, False)

    def test_503_is_gateway_error(self):
        with self.assertRaises(errors.ServiceGatewayError) as ctx:
            self._call(503, reason='Service Unavailable')
        self.assertIsInstance(ctx.exception, errors.TransientError)
        self.assertEqual(ctx.exception.retryable, True)

    def test_other_status_still_legacy_request_error(self):
        # status codes we did not specifically classify keep the previous
        # behaviour (legacy RequestError) — unchanged on purpose.
        with self.assertRaises(errors.RequestError):
            self._call(418, reason="I'm a teapot")


class TestGoogleErrorMapping(unittest.TestCase):
    """service_google.get_tts_audio HTTP-status -> error mapping."""

    def setUp(self):
        self.google_service = service_google.Google()
        self.google_service._config = {'api_key': 'fake_api_key'}
        self.voice = _make_voice(
            options={'speaking_rate': {'default': 1.0}},
            voice_key={'name': 'en-US-Standard-A', 'language_code': 'en-US'})

    def _call(self, status_code, json_body, text=''):
        mock_response = mock.Mock()
        mock_response.status_code = status_code
        mock_response.text = text
        mock_response.json.return_value = json_body
        with mock.patch('requests.post', return_value=mock_response):
            return self.google_service.get_tts_audio('Test text', self.voice, {})

    def test_403_billing_not_enabled_is_permission_error(self):
        # ANKI-HYPER-TTS-HHQ
        message = ('This API method requires billing to be enabled. Please '
                   'enable billing on project #865206007149 ... then retry.')
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            self._call(403, {'error': {'message': message}})
        self.assertIsInstance(ctx.exception, errors.PermanentError)
        self.assertEqual(ctx.exception.retryable, False)
        self.assertIn('billing to be enabled', ctx.exception.error_message)

    def test_401_is_permission_error(self):
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            self._call(401, {'error': {'message': 'API key not valid'}})
        self.assertEqual(ctx.exception.retryable, False)

    def test_other_status_still_legacy_request_error(self):
        with self.assertRaises(errors.RequestError):
            self._call(500, {'error': {'message': 'internal error'}})


class TestGeminiContentBlockMapping(unittest.TestCase):
    """service_gemini.get_tts_audio content-policy refusal mapping."""

    def setUp(self):
        self.gemini_service = service_gemini.Gemini()
        self.gemini_service._config = {'api_key': 'fake_api_key'}
        self.voice = _make_voice(
            options={
                'model': {'default': 'gemini-2.5-flash-tts'},
                'prompt': {'default': ''},
                'language_code': {'default': 'en-US'},
            },
            voice_key={'name': 'Gacrux'})

    def _call(self, json_body, status_code=200):
        mock_response = mock.Mock()
        mock_response.status_code = status_code
        mock_response.text = str(json_body)
        mock_response.headers = {}
        mock_response.json.return_value = json_body
        with mock.patch('requests.post', return_value=mock_response):
            return self.gemini_service.get_tts_audio('Test text', self.voice, {})

    def test_prompt_feedback_block_reason_is_input_error(self):
        # ANKI-HYPER-TTS-HT9: HTTP 200, no audio, content was blocked.
        body = {'promptFeedback': {'blockReason': 'PROHIBITED_CONTENT'},
                'usageMetadata': {'promptTokenCount': 13}}
        with self.assertRaises(errors.ServiceInputError) as ctx:
            self._call(body)
        self.assertIsInstance(ctx.exception, errors.PermanentError)
        self.assertEqual(ctx.exception.retryable, False)
        self.assertIn('PROHIBITED_CONTENT', ctx.exception.error_message)

    def test_candidate_finish_reason_safety_is_input_error(self):
        body = {'candidates': [{'finishReason': 'SAFETY'}]}
        with self.assertRaises(errors.ServiceInputError) as ctx:
            self._call(body)
        self.assertEqual(ctx.exception.retryable, False)
        self.assertIn('SAFETY', ctx.exception.error_message)

    def test_unexpected_empty_payload_still_legacy_request_error(self):
        # genuinely unexpected payload (not a content block) keeps the
        # previous behaviour so we still see it surface in triage
        with self.assertRaises(errors.RequestError):
            self._call({'unexpected': 'shape'})


if __name__ == '__main__':
    unittest.main()
