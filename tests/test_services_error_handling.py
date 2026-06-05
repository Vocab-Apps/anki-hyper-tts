#!/usr/bin/env python3
"""Unit tests for HTTP-status -> error categorization in TTS services.

These cover the mis-categorizations found during the Sentry audio-error
review (ANKI-HYPER-TTS-HHQ / HHA / HT9 / JY0 / JY4): cases that used to be
raised as the legacy, non-retry-aware ``RequestError`` and are now mapped to
the correct permanent / transient ``ServiceRequestError`` subclass.
"""

import unittest
import unittest.mock as mock

import botocore.exceptions

from hypertts_addon.services import service_alibaba
from hypertts_addon.services import service_amazon
from hypertts_addon.services import service_azure
from hypertts_addon.services import service_google
from hypertts_addon.services import service_googletranslate
from hypertts_addon.services import service_gemini
from hypertts_addon.services import service_elevenlabscustom
from hypertts_addon import logging_utils
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages

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

    def test_429_resource_exhausted_is_rate_limit(self):
        # ANKI-HYPER-TTS-HHQ: Google Cloud TTS responds with HTTP 429 +
        # "Resource has been exhausted (e.g. check quota)." when the per-minute
        # quota is hit. Previously raised as legacy RequestError, which kept it
        # out of the retry logic; now it's a transient RateLimitRetryAfterError.
        message = 'Resource has been exhausted (e.g. check quota).'
        with self.assertRaises(errors.RateLimitRetryAfterError) as ctx:
            self._call(429, {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED',
                                       'message': message}})
        self.assertIsInstance(ctx.exception, errors.TransientError)
        self.assertEqual(ctx.exception.retryable, True)
        self.assertEqual(ctx.exception.retry_after,
                         service_google.GOOGLE_RATE_LIMIT_DEFAULT_RETRY_AFTER)
        self.assertIn('Resource has been exhausted', ctx.exception.error_message)

    def test_other_status_still_legacy_request_error(self):
        with self.assertRaises(errors.RequestError):
            self._call(500, {'error': {'message': 'internal error'}})


class TestGoogleTranslateLocaleHandling(unittest.TestCase):
    """service_googletranslate must preserve regional language tags."""

    def setUp(self):
        self.service = service_googletranslate.GoogleTranslate()

    def _voice_for_language(self, audio_language):
        with mock.patch(
                'hypertts_addon.services.service_googletranslate.gtts.lang.tts_langs',
                return_value={
                    'pt': 'Portuguese (Brazil)',
                    'pt-PT': 'Portuguese (Portugal)',
                    'fr': 'French',
                    'fr-CA': 'French (Canada)',
                }):
            return [
                voice for voice in self.service.voice_list()
                if voice.audio_languages == [audio_language]
            ][0]

    def test_voice_list_keeps_regional_google_translate_keys(self):
        portuguese_brazil = self._voice_for_language(languages.AudioLanguage.pt_BR)
        portuguese_portugal = self._voice_for_language(languages.AudioLanguage.pt_PT)
        french_canada = self._voice_for_language(languages.AudioLanguage.fr_CA)

        self.assertEqual(portuguese_brazil.voice_key, 'pt')
        self.assertEqual(portuguese_portugal.voice_key, 'pt-PT')
        self.assertEqual(french_canada.voice_key, 'fr-CA')

    def test_audio_generation_preserves_portuguese_portugal_key(self):
        voice = self._voice_for_language(languages.AudioLanguage.pt_PT)

        with mock.patch(
                'hypertts_addon.services.service_googletranslate.gtts.gTTS'
        ) as mock_gtts:
            mock_gtts.return_value.write_to_fp.side_effect = lambda fp: fp.write(b'audio')

            audio = self.service.get_tts_audio('bom dia a todos', voice, {})

        self.assertEqual(bytes(audio), b'audio')
        mock_gtts.assert_called_once_with(
            text='bom dia a todos',
            lang='pt-PT',
            lang_check=False,
            timeout=constants.RequestTimeout)

    def test_audio_generation_preserves_french_canada_key(self):
        voice = self._voice_for_language(languages.AudioLanguage.fr_CA)

        with mock.patch(
                'hypertts_addon.services.service_googletranslate.gtts.gTTS'
        ) as mock_gtts:
            mock_gtts.return_value.write_to_fp.side_effect = lambda fp: fp.write(b'audio')

            audio = self.service.get_tts_audio("Le son de la voix n'est pas correct.", voice, {})

        self.assertEqual(bytes(audio), b'audio')
        mock_gtts.assert_called_once_with(
            text="Le son de la voix n'est pas correct.",
            lang='fr-CA',
            lang_check=False,
            timeout=constants.RequestTimeout)


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

    def test_candidate_finish_reason_other_is_input_error(self):
        # ANKI-HYPER-TTS-HT9: Gemini 200 with `finishReason: 'OTHER'` and no
        # `content` key on the candidate — observed consistently for the same
        # input text across many users. Treated as a permanent refusal; was
        # previously surfaced as legacy non-retry-aware RequestError.
        body = {
            'candidates': [{'finishReason': 'OTHER', 'index': 0}],
            'usageMetadata': {'promptTokenCount': 3, 'totalTokenCount': 3},
            'modelVersion': 'gemini-2.5-flash-preview-tts',
        }
        with self.assertRaises(errors.ServiceInputError) as ctx:
            self._call(body)
        self.assertIsInstance(ctx.exception, errors.PermanentError)
        self.assertEqual(ctx.exception.retryable, False)
        self.assertIn('OTHER', ctx.exception.error_message)

    def test_unexpected_empty_payload_still_legacy_request_error(self):
        # genuinely unexpected payload (not a content block) keeps the
        # previous behaviour so we still see it surface in triage
        with self.assertRaises(errors.RequestError):
            self._call({'unexpected': 'shape'})


class TestElevenLabsCustomErrorMapping(unittest.TestCase):
    """service_elevenlabscustom.get_tts_audio HTTP-status -> error mapping."""

    def setUp(self):
        self.service = service_elevenlabscustom.ElevenLabsCustom()
        self.service._config = {'api_key': 'fake_api_key'}
        self.voice = _make_voice(
            options={
                'stability': {'default': 0.5},
                'similarity_boost': {'default': 0.75},
                'style': {'default': 0.0},
                'speed': {'default': 1.0},
                'use_speaker_boost': {'default': 'false'},
                'language_code': {'default': ''},
                'format': {'default': 'mp3'},
            },
            voice_key={'voice_id': 'fake_voice_id', 'model_id': 'eleven_turbo_v2_5'})

    def _call(self, status_code, text='', voice_options=None):
        mock_response = mock.Mock()
        mock_response.status_code = status_code
        mock_response.text = text
        with mock.patch('requests.post', return_value=mock_response):
            return self.service.get_tts_audio(
                'Test text', self.voice, voice_options if voice_options is not None else {})

    def test_400_validation_error_is_input_error(self):
        # ANKI-HYPER-TTS-HGT: HTTP 400 with
        # {"detail":{"type":"validation_error","code":"invalid_parameters",
        #  "message":"Model 'eleven_turbo_v2_5' does not support language_code 'ell'.",
        #  "status":"unsupported_language", ...}}
        # Permanent — retrying the same combination of model + language will
        # always fail. Was previously legacy RequestError.
        body = ('{"detail":{"type":"validation_error","code":"invalid_parameters",'
                '"message":"Model \'eleven_turbo_v2_5\' does not support language_code \'ell\'.",'
                '"status":"unsupported_language"}}')
        with self.assertRaises(errors.ServiceInputError) as ctx:
            self._call(400, text=body, voice_options={'language_code': 'ell'})
        self.assertIsInstance(ctx.exception, errors.PermanentError)
        self.assertEqual(ctx.exception.retryable, False)
        self.assertIn('400', ctx.exception.error_message)
        self.assertIn('unsupported_language', ctx.exception.error_message)

    def test_401_is_permission_error(self):
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            self._call(401, text='Unauthorized')
        self.assertEqual(ctx.exception.retryable, False)

    def test_402_is_permission_error(self):
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            self._call(402, text='Payment Required')
        self.assertEqual(ctx.exception.retryable, False)

    def test_other_status_still_legacy_request_error(self):
        # 5xx and unclassified codes still go through the legacy RequestError
        # path so they remain visible in triage.
        with self.assertRaises(errors.RequestError):
            self._call(500, text='internal server error')


class TestAlibabaErrorMapping(unittest.TestCase):
    """service_alibaba refresh_token + get_tts_audio HTTP-status -> error mapping."""

    def setUp(self):
        self.alibaba_service = service_alibaba.Alibaba()
        self.alibaba_service._config = {
            'access_key_id': 'fake_id',
            'access_key_secret': 'fake_secret',
            'app_key': 'fake_app_key',
        }
        self.voice = _make_voice(
            options={'speed': {'default': 0}, 'pitch': {'default': 0}},
            voice_key={'name': 'Andy'},
        )

    def _call_refresh(self, status_code, text='', json_body=None):
        mock_response = mock.Mock()
        mock_response.status_code = status_code
        mock_response.text = text
        if json_body is not None:
            mock_response.json.return_value = json_body
        with mock.patch('requests.get', return_value=mock_response):
            return self.alibaba_service.refresh_token('Test text', self.voice)

    def _call_tts(self, status_code, json_body=None, headers=None, content=b''):
        mock_response = mock.Mock()
        mock_response.status_code = status_code
        mock_response.headers = {'Content-Type': 'audio/mpeg'} if headers is None else headers
        mock_response.content = content
        mock_response.text = '' if json_body is None else str(json_body)
        if json_body is not None:
            mock_response.json.return_value = json_body
        self.alibaba_service.access_token = {'Id': 'fake-token', 'ExpireTime': 9999999999}
        with mock.patch('requests.get', return_value=mock_response):
            return self.alibaba_service.get_tts_audio('Test text', self.voice, {})

    def test_refresh_token_404_access_key_not_found_is_permission_error(self):
        # ANKI-HYPER-TTS-JY4: HTTP 404 from the CreateToken endpoint with body
        # {"Code":"InvalidAccessKeyId.NotFound","Message":"Specified access key
        # is not found."} — auth failure, not "audio missing". Was previously
        # raised as legacy RequestError.
        body = ('{"RequestId":"14B25401-7028-38DC-A8AE-C813A6D60FEA",'
                '"Message":"Specified access key is not found.",'
                '"HostId":"nlsmeta.ap-southeast-1.aliyuncs.com",'
                '"Code":"InvalidAccessKeyId.NotFound"}')
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            self._call_refresh(404, text=body)
        self.assertIsInstance(ctx.exception, errors.PermanentError)
        self.assertEqual(ctx.exception.retryable, False)
        self.assertIn('404', str(ctx.exception))
        self.assertIn('InvalidAccessKeyId.NotFound', str(ctx.exception))

    def test_refresh_token_401_is_permission_error(self):
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            self._call_refresh(401, text='Unauthorized')
        self.assertEqual(ctx.exception.retryable, False)

    def test_refresh_token_403_is_permission_error(self):
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            self._call_refresh(403, text='Forbidden')
        self.assertEqual(ctx.exception.retryable, False)

    def test_refresh_token_503_is_gateway_error(self):
        with self.assertRaises(errors.ServiceGatewayError) as ctx:
            self._call_refresh(503, text='unavailable')
        self.assertIsInstance(ctx.exception, errors.TransientError)
        self.assertEqual(ctx.exception.retryable, True)

    def test_refresh_token_500_is_unknown_service_error(self):
        with self.assertRaises(errors.UnknownServiceError) as ctx:
            self._call_refresh(500, text='internal error')
        self.assertEqual(ctx.exception.retryable, True)

    def test_refresh_token_missing_token_in_response_is_unknown_service_error(self):
        with self.assertRaises(errors.UnknownServiceError) as ctx:
            self._call_refresh(200, json_body={'RequestId': 'abc'})
        self.assertEqual(ctx.exception.retryable, True)
        self.assertIn('no Token in response', ctx.exception.error_message)

    def test_tts_403_is_permission_error(self):
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            self._call_tts(403, json_body={'message': 'forbidden'})
        self.assertEqual(ctx.exception.retryable, False)

    def test_tts_502_is_gateway_error(self):
        with self.assertRaises(errors.ServiceGatewayError) as ctx:
            self._call_tts(502, json_body={'message': 'bad gateway'})
        self.assertEqual(ctx.exception.retryable, True)

    def test_tts_500_is_unknown_service_error(self):
        with self.assertRaises(errors.UnknownServiceError) as ctx:
            self._call_tts(500, json_body={'message': 'internal'})
        self.assertEqual(ctx.exception.retryable, True)

    def test_tts_bad_content_type_is_unknown_service_error(self):
        with self.assertRaises(errors.UnknownServiceError) as ctx:
            self._call_tts(200, headers={'Content-Type': 'application/json'})
        self.assertEqual(ctx.exception.retryable, True)
        self.assertIn('bad content type', ctx.exception.error_message)


class TestAmazonErrorMapping(unittest.TestCase):
    """service_amazon ClientError code -> error mapping."""

    def setUp(self):
        self.amazon_service = service_amazon.Amazon()
        self.amazon_service._config = {
            'aws_access_key_id': 'fake_key',
            'aws_secret_access_key': 'fake_secret',
            'aws_region': 'us-east-1',
        }
        # Bypass configure() so we don't construct a real boto3 client.
        self.amazon_service.polly_client = mock.Mock()
        self.voice = _make_voice(
            options={'pitch': {'default': 0}, 'rate': {'default': 100}},
            voice_key={'voice_id': 'Zhiyu', 'engine': 'neural'},
        )

    def _make_client_error(self, code, message='', http_status=400):
        error_response = {
            'Error': {'Code': code, 'Message': message},
            'ResponseMetadata': {'HTTPStatusCode': http_status},
        }
        return botocore.exceptions.ClientError(error_response, 'SynthesizeSpeech')

    def _raise_on_synth(self, error):
        self.amazon_service.polly_client.synthesize_speech.side_effect = error

    def _call(self):
        return self.amazon_service.get_tts_audio('Test text', self.voice, {})

    def test_invalid_ssml_exception_is_input_error(self):
        # ANKI-HYPER-TTS-JY0: InvalidSsmlException from a malformed nested
        # <speak> + <phoneme> SSML block. Retrying the same input will always
        # fail. Was previously legacy RequestError.
        self._raise_on_synth(self._make_client_error(
            'InvalidSsmlException', 'Invalid SSML request'))
        with self.assertRaises(errors.ServiceInputError) as ctx:
            self._call()
        self.assertIsInstance(ctx.exception, errors.PermanentError)
        self.assertEqual(ctx.exception.retryable, False)
        self.assertIn('InvalidSsmlException', str(ctx.exception))

    def test_text_length_exceeded_is_input_error(self):
        self._raise_on_synth(self._make_client_error(
            'TextLengthExceededException', 'Input text too long'))
        with self.assertRaises(errors.ServiceInputError) as ctx:
            self._call()
        self.assertEqual(ctx.exception.retryable, False)

    def test_language_not_supported_is_input_error(self):
        self._raise_on_synth(self._make_client_error(
            'LanguageNotSupportedException', 'Language not supported by voice'))
        with self.assertRaises(errors.ServiceInputError) as ctx:
            self._call()
        self.assertEqual(ctx.exception.retryable, False)

    def test_access_denied_is_permission_error(self):
        self._raise_on_synth(self._make_client_error(
            'AccessDeniedException', 'User is not authorized', http_status=403))
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            self._call()
        self.assertEqual(ctx.exception.retryable, False)

    def test_unrecognized_client_is_permission_error(self):
        self._raise_on_synth(self._make_client_error(
            'UnrecognizedClientException', 'Security token invalid', http_status=403))
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            self._call()
        self.assertEqual(ctx.exception.retryable, False)

    def test_unknown_client_error_falls_back_to_unknown_service_error(self):
        self._raise_on_synth(self._make_client_error(
            'ThrottlingException', 'Rate exceeded', http_status=429))
        with self.assertRaises(errors.UnknownServiceError) as ctx:
            self._call()
        self.assertIsInstance(ctx.exception, errors.TransientError)
        self.assertEqual(ctx.exception.retryable, True)

    def test_endpoint_connection_error_is_connection_error(self):
        self._raise_on_synth(
            botocore.exceptions.EndpointConnectionError(endpoint_url='https://polly.us-east-1.amazonaws.com/'))
        with self.assertRaises(errors.ServiceConnectionError) as ctx:
            self._call()
        self.assertEqual(ctx.exception.retryable, True)

    def test_read_timeout_is_timeout_error(self):
        self._raise_on_synth(
            botocore.exceptions.ReadTimeoutError(endpoint_url='https://polly.us-east-1.amazonaws.com/'))
        with self.assertRaises(errors.ServiceTimeoutError) as ctx:
            self._call()
        self.assertEqual(ctx.exception.retryable, True)

    def test_missing_audio_stream_is_unknown_service_error(self):
        # No exception from polly, but response also lacks AudioStream.
        self.amazon_service.polly_client.synthesize_speech.return_value = {}
        with self.assertRaises(errors.UnknownServiceError) as ctx:
            self._call()
        self.assertEqual(ctx.exception.retryable, True)
        self.assertIn('no audio stream', ctx.exception.error_message)


if __name__ == '__main__':
    unittest.main()
