import copy
import io
import json
import wave
import base64
import unittest
import pytest
from unittest.mock import patch, MagicMock

import magic

from .base import TTSTests, logger
from hypertts_addon import constants
from hypertts_addon import context
from hypertts_addon import errors
from hypertts_addon import languages
from hypertts_addon import voice as voice_module
from hypertts_addon.services.service_gemini import (
    Gemini,
    GEMINI_3_8_MODELS,
    GEMINI_PCM_SAMPLE_RATE,
    _extract_retry_after_seconds,
    _raise_for_error_status,
    DEFAULT_RETRY_AFTER_SECONDS,
)


class TestGemini(TTSTests):

    SERVICE_NAME = 'Gemini'

    def test_voice_list(self):
        voice_list = self.manager.full_voice_list()
        gemini_voices = [voice for voice in voice_list if voice.service == self.SERVICE_NAME]
        logger.info(f'found {len(gemini_voices)} voices for Gemini services')
        assert len(gemini_voices) >= 30

    def test_english(self):
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence')

    def test_french(self):
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.fr_FR
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'Je ne suis pas disponible.',
                                 voice_options={'language_code': 'fr-FR'})

    def test_japanese(self):
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.ja_JP
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'おはようございます',
                                 voice_options={'language_code': 'ja-JP'})

    @pytest.mark.skip(reason="ogg is actually supported on the CLT backend")
    def test_ogg_opus_unsupported(self):
        # ogg_opus format — not supported by Gemini service, should raise ServiceInputError
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        exception_caught = False
        try:
            self.manager.get_tts_audio('This is the first sentence', selected_voice,
                {'format': 'ogg_opus'},
                context.AudioRequestContext(constants.AudioRequestReason.batch))
        except errors.ServiceInputError as e:
            assert e.source_text == 'This is the first sentence'
            assert e.voice.service == self.SERVICE_NAME
            exception_caught = True
        assert exception_caught

    def test_voice_list_models(self):
        # the default model is gemini 3.8 flash, and the 3.8 models come first
        voice_list = self.manager.full_voice_list()
        gemini_voices = [voice for voice in voice_list if voice.service == self.SERVICE_NAME]
        for voice in gemini_voices:
            model_option = voice.options['model']
            self.assertEqual(model_option['default'], 'gemini-3.8-flash-tts')
            self.assertEqual(model_option['values'][:2], ['gemini-3.8-flash-tts', 'gemini-3.8-flash-lite-tts'])
            self.assertIn('mp3_hq', voice.options['format']['values'])

    def test_model_gemini_3_8_flash_tts(self):
        # pytest tests/test_tts_services/ -k 'TestGemini and test_model_gemini_3_8_flash_tts'
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'model': 'gemini-3.8-flash-tts'})

    def test_model_gemini_3_8_flash_lite_tts(self):
        # pytest tests/test_tts_services/ -k 'TestGemini and test_model_gemini_3_8_flash_lite_tts'
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'model': 'gemini-3.8-flash-lite-tts'})

    def test_model_gemini_3_8_prompt_and_language_code(self):
        # the 3.8 models take the style prompt as speech metadata rather than inline, the
        # audio should still transcribe to the source text only
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.fr_FR
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'Je ne suis pas disponible.',
                                 voice_options={'model': 'gemini-3.8-flash-tts', 'language_code': 'fr-FR',
                                                'prompt': 'Speak in a cheerful, upbeat tone'})

    def test_mp3_hq(self):
        # pytest tests/test_tts_services/ -k 'TestGemini and test_mp3_hq'
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'format': 'mp3_hq'})

    def test_model_gemini_3_1_flash_tts_preview(self):
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'model': 'gemini-3.1-flash-tts-preview'})

    def test_model_gemini_2_5_flash_tts(self):
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'model': 'gemini-2.5-flash-tts'})

    def test_model_gemini_2_5_pro_tts(self):
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'model': 'gemini-2.5-pro-tts'})

    def test_model_gemini_2_5_flash_lite_preview_tts(self):
        if self.CONFIG_MODE != 'clt':
            pytest.skip('gemini-2.5-flash-lite-preview-tts is not available on the Gemini API (direct mode)')
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'model': 'gemini-2.5-flash-lite-preview-tts'})

    def test_language_code_override(self):
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'Guten Morgen',
                                 voice_options={'language_code': 'de-DE'})

    def test_prompt_style_control(self):
        # prompt (voice style control) — audio should still transcribe to the source text
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'prompt': 'Speak in a cheerful, upbeat tone'})

    def test_invalid_voice_name(self):
        voice_list = self.manager.full_voice_list()
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, languages.AudioLanguage.en_US)
        selected_voice = copy.copy(selected_voice)
        voice_key = copy.copy(selected_voice.voice_key)
        voice_key['name'] = 'non existent'
        altered_voice = voice_module.TtsVoice_v3('non existent',
                                                 voice_key,
                                                 selected_voice.options,
                                                 self.SERVICE_NAME,
                                                 selected_voice.gender,
                                                 [languages.AudioLanguage.en_US],
                                                 constants.ServiceFee.paid)

        exception_caught = False
        try:
            self.manager.get_tts_audio('This is the second sentence', altered_voice, {},
                context.AudioRequestContext(constants.AudioRequestReason.batch))
        except (errors.RequestError, errors.ServiceRequestError) as e:
            assert e.source_text == 'This is the second sentence'
            assert e.voice.service == self.SERVICE_NAME
            exception_caught = True
        assert exception_caught


class TestGeminiCLT(TestGemini):
    CONFIG_MODE = 'clt'


def build_wav_bytes(duration_seconds=0.2, sample_rate=GEMINI_PCM_SAMPLE_RATE):
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b'\x00\x00' * int(duration_seconds * sample_rate))
    return buffer.getvalue()


def build_generate_content_response(audio_bytes, mime_type):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        'candidates': [{
            'content': {
                'role': 'model',
                'parts': [{
                    'inlineData': {
                        'mimeType': mime_type,
                        'data': base64.b64encode(audio_bytes).decode('ascii'),
                    }
                }]
            },
            'finishReason': 'STOP',
        }]
    }
    return response


@patch('hypertts_addon.services.service_gemini.requests.post')
class TestGeminiRequestShape(unittest.TestCase):
    """Mock tests for the request payload and audio handling: the 3.8 models use a
    different request schema and return WAV instead of headerless PCM."""

    VOICE_OPTIONS = {
        'model': {'type': 'list', 'values': ['gemini-3.8-flash-tts', 'gemini-3.8-flash-lite-tts', 'gemini-2.5-flash-tts'], 'default': 'gemini-3.8-flash-tts'},
        'language_code': {'type': 'text', 'default': 'en-US'},
        'prompt': {'type': 'text', 'default': ''},
        'format': {'type': 'list', 'values': ['mp3', 'mp3_hq', 'ogg_opus'], 'default': 'mp3'},
    }

    def setUp(self):
        self.service = Gemini()
        self.service.configure({'api_key': 'fake_key'})
        self.voice = voice_module.TtsVoice_v3('Kore', {'name': 'Kore'}, self.VOICE_OPTIONS, 'Gemini',
            constants.Gender.Female, [languages.AudioLanguage.en_US], constants.ServiceFee.paid)

    def get_request(self, mock_post):
        self.assertEqual(mock_post.call_count, 1)
        args, kwargs = mock_post.call_args
        return args[0], kwargs

    def assert_mp3_hq(self, audio_data):
        file_type = magic.from_buffer(audio_data)
        self.assertIn('MPEG ADTS, layer III', file_type)
        self.assertIn(f'{constants.AUDIO_MP3_HQ_ENCODE_BITRATE_KBPS} kbps', file_type)

    def test_3_8_default_model_payload(self, mock_post):
        mock_post.return_value = build_generate_content_response(build_wav_bytes(), 'audio/wav')

        audio_data = self.service.get_tts_audio('hello', self.voice, {})

        url, kwargs = self.get_request(mock_post)
        self.assertEqual(url, 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent')
        self.assertEqual(kwargs['headers']['x-goog-api-key'], 'fake_key')
        self.assertEqual(kwargs['json'], {
            'contents': [{'parts': [{'text': 'hello'}]}],
            'generationConfig': {
                'responseModalities': ['AUDIO'],
                'speechConfig': {'voiceConfig': {'voice': 'Kore'}, 'languageCode': 'en-US'},
            },
            'model': 'gemini-3.8-flash-tts',
        })
        # the WAV response is encoded to mp3 at the high quality bitrate, there is no native mp3
        self.assert_mp3_hq(audio_data)

    def test_3_8_prompt_goes_in_speech_metadata(self, mock_post):
        mock_post.return_value = build_generate_content_response(build_wav_bytes(), 'audio/wav')

        self.service.get_tts_audio('bonjour', self.voice,
            {'model': 'gemini-3.8-flash-lite-tts', 'prompt': 'calm and warm', 'language_code': 'fr-FR'})

        url, kwargs = self.get_request(mock_post)
        self.assertIn('gemini-3.8-flash-lite-tts:generateContent', url)
        body = kwargs['json']
        self.assertEqual(body['contents'][0]['parts'][0], {'text': 'bonjour', 'speechMetadata': {'style': 'calm and warm'}})
        self.assertEqual(body['generationConfig']['speechConfig'], {'voiceConfig': {'voice': 'Kore'}, 'languageCode': 'fr-FR'})

    def test_3_8_empty_language_code_is_omitted(self, mock_post):
        mock_post.return_value = build_generate_content_response(build_wav_bytes(), 'audio/wav')

        self.service.get_tts_audio('hello', self.voice, {'language_code': ''})

        url, kwargs = self.get_request(mock_post)
        self.assertEqual(kwargs['json']['generationConfig']['speechConfig'], {'voiceConfig': {'voice': 'Kore'}})

    def test_2_5_model_payload(self, mock_post):
        # the older models: prebuilt voice config, prompt inline, API model id translated
        pcm_bytes = b'\x00\x00' * int(0.2 * GEMINI_PCM_SAMPLE_RATE)
        mock_post.return_value = build_generate_content_response(pcm_bytes, 'audio/L16;codec=pcm;rate=24000')

        audio_data = self.service.get_tts_audio('hello', self.voice, {'model': 'gemini-2.5-flash-tts', 'prompt': 'cheerful'})

        url, kwargs = self.get_request(mock_post)
        self.assertEqual(url, 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent')
        self.assertEqual(kwargs['json'], {
            'contents': [{'parts': [{'text': 'cheerful: hello'}]}],
            'generationConfig': {
                'responseModalities': ['AUDIO'],
                'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': 'Kore'}}, 'languageCode': 'en-US'},
            },
            'model': 'gemini-2.5-flash-preview-tts',
        })
        self.assert_mp3_hq(audio_data)

    def test_mp3_hq_format(self, mock_post):
        mock_post.return_value = build_generate_content_response(build_wav_bytes(), 'audio/wav')

        audio_data = self.service.get_tts_audio('hello', self.voice, {'format': 'mp3_hq'})

        self.assert_mp3_hq(audio_data)

    def test_ogg_opus_unsupported(self, mock_post):
        with self.assertRaises(errors.ServiceInputError):
            self.service.get_tts_audio('hello', self.voice, {'format': 'ogg_opus'})
        mock_post.assert_not_called()

    def test_all_3_8_models_use_new_schema(self, mock_post):
        for model in GEMINI_3_8_MODELS:
            with self.subTest(model=model):
                mock_post.reset_mock()
                mock_post.return_value = build_generate_content_response(build_wav_bytes(), 'audio/wav')
                self.service.get_tts_audio('hello', self.voice, {'model': model})
                url, kwargs = self.get_request(mock_post)
                self.assertIn(f'{model}:generateContent', url)
                self.assertEqual(kwargs['json']['generationConfig']['speechConfig']['voiceConfig'], {'voice': 'Kore'})


class TestGeminiRetryAfterParsing(unittest.TestCase):

    def _payload(self, details):
        return json.dumps({'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED',
                                     'message': 'rate limited', 'details': details}})

    def test_parses_integer_seconds(self):
        body = self._payload([
            {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': []},
            {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '25s'},
        ])
        self.assertEqual(_extract_retry_after_seconds(body), 25)

    def test_parses_fractional_seconds_ceils(self):
        body = self._payload([
            {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '24.18243361s'},
        ])
        self.assertEqual(_extract_retry_after_seconds(body), 25)

    def test_missing_retry_info_returns_default(self):
        body = self._payload([
            {'@type': 'type.googleapis.com/google.rpc.Help', 'links': []},
        ])
        self.assertEqual(_extract_retry_after_seconds(body), DEFAULT_RETRY_AFTER_SECONDS)

    def test_missing_details_returns_default(self):
        body = json.dumps({'error': {'code': 429, 'message': 'rate limited'}})
        self.assertEqual(_extract_retry_after_seconds(body), DEFAULT_RETRY_AFTER_SECONDS)

    def test_malformed_json_returns_default(self):
        body = '<html><body>429 Too Many Requests</body></html>'
        self.assertEqual(_extract_retry_after_seconds(body), DEFAULT_RETRY_AFTER_SECONDS)

    def test_empty_string_returns_default(self):
        self.assertEqual(_extract_retry_after_seconds(''), DEFAULT_RETRY_AFTER_SECONDS)


class TestGeminiErrorStatusMapping(unittest.TestCase):
    # Regression tests for the non-200 response → exception mapping.
    # Before the fix for Sentry ANKI-HYPER-TTS-K4V, every non-200 response
    # was raised as the legacy errors.RequestError (not retry-aware), so
    # permanent failures like 403 "User location is not supported" were
    # retried 3× and grouped under the legacy class.

    SOURCE_TEXT = 'pants(美)'
    VOICE = 'Achernar (Soft) (Gemini)'

    def _error_body(self, status_code, message, status_string=None):
        error = {'code': status_code, 'message': message}
        if status_string is not None:
            error['status'] = status_string
        return json.dumps({'error': error})

    def test_k4v_user_location_not_supported_is_permission_error(self):
        # The exact failure from Sentry ANKI-HYPER-TTS-K4V: Gemini returns
        # 403 PERMISSION_DENIED when the caller's geographic region is not
        # supported. Retrying never helps.
        body = self._error_body(403, 'User location is not supported for the API use.',
                                status_string='PERMISSION_DENIED')
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            _raise_for_error_status(403, body, self.SOURCE_TEXT, self.VOICE)
        self.assertFalse(ctx.exception.retryable)
        self.assertEqual(ctx.exception.source_text, self.SOURCE_TEXT)
        self.assertIn('User location is not supported', ctx.exception.error_message)
        self.assertIn('HTTP 403', ctx.exception.error_message)

    def test_401_unauthenticated_is_permission_error(self):
        body = self._error_body(401, 'API key not valid.', status_string='UNAUTHENTICATED')
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            _raise_for_error_status(401, body, self.SOURCE_TEXT, self.VOICE)
        self.assertFalse(ctx.exception.retryable)

    def test_400_invalid_argument_is_input_error(self):
        body = self._error_body(400, 'Invalid voice name.', status_string='INVALID_ARGUMENT')
        with self.assertRaises(errors.ServiceInputError) as ctx:
            _raise_for_error_status(400, body, self.SOURCE_TEXT, self.VOICE)
        self.assertFalse(ctx.exception.retryable)

    def test_404_not_found_is_permission_error(self):
        body = self._error_body(404, 'Model not found.', status_string='NOT_FOUND')
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            _raise_for_error_status(404, body, self.SOURCE_TEXT, self.VOICE)
        self.assertFalse(ctx.exception.retryable)

    def test_500_internal_is_gateway_error(self):
        body = self._error_body(500, 'Internal error.', status_string='INTERNAL')
        with self.assertRaises(errors.ServiceGatewayError) as ctx:
            _raise_for_error_status(500, body, self.SOURCE_TEXT, self.VOICE)
        self.assertTrue(ctx.exception.retryable)

    def test_503_unavailable_is_gateway_error(self):
        body = self._error_body(503, 'Service unavailable.', status_string='UNAVAILABLE')
        with self.assertRaises(errors.ServiceGatewayError) as ctx:
            _raise_for_error_status(503, body, self.SOURCE_TEXT, self.VOICE)
        self.assertTrue(ctx.exception.retryable)

    def test_504_deadline_exceeded_is_gateway_error(self):
        body = self._error_body(504, 'Deadline exceeded.', status_string='DEADLINE_EXCEEDED')
        with self.assertRaises(errors.ServiceGatewayError) as ctx:
            _raise_for_error_status(504, body, self.SOURCE_TEXT, self.VOICE)
        self.assertTrue(ctx.exception.retryable)

    def test_unknown_status_is_unknown_service_error(self):
        # 418 is not in any of the specific buckets — fall through to
        # UnknownServiceError (transient) so the retry loop gets a chance.
        body = self._error_body(418, "I'm a teapot.")
        with self.assertRaises(errors.UnknownServiceError) as ctx:
            _raise_for_error_status(418, body, self.SOURCE_TEXT, self.VOICE)
        self.assertTrue(ctx.exception.retryable)

    def test_malformed_json_body_still_maps_by_status(self):
        # Some upstream errors (e.g. proxy/load-balancer pages) return
        # non-JSON bodies. The mapping must still choose by status code.
        body = '<html><body>503 Service Unavailable</body></html>'
        with self.assertRaises(errors.ServiceGatewayError) as ctx:
            _raise_for_error_status(503, body, self.SOURCE_TEXT, self.VOICE)
        self.assertIn('503 Service Unavailable', ctx.exception.error_message)

    def test_empty_body_still_maps_by_status(self):
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            _raise_for_error_status(403, '', self.SOURCE_TEXT, self.VOICE)
        self.assertIn('HTTP 403', ctx.exception.error_message)

    def test_json_without_error_field_uses_full_body_as_message(self):
        body = json.dumps({'unexpected': 'shape'})
        with self.assertRaises(errors.ServicePermissionError) as ctx:
            _raise_for_error_status(403, body, self.SOURCE_TEXT, self.VOICE)
        self.assertIn('unexpected', ctx.exception.error_message)

    def test_all_mapped_exceptions_are_service_request_errors(self):
        # Sanity check: every class we raise must be a ServiceRequestError
        # subclass so servicemanager's instrumentation tags it correctly with
        # is_audio_request_exception=True and the right error_retryable flag.
        cases = [
            (400, errors.ServiceInputError),
            (401, errors.ServicePermissionError),
            (403, errors.ServicePermissionError),
            (404, errors.ServicePermissionError),
            (500, errors.ServiceGatewayError),
            (503, errors.ServiceGatewayError),
            (504, errors.ServiceGatewayError),
            (418, errors.UnknownServiceError),
        ]
        for status, expected_cls in cases:
            with self.subTest(status=status):
                with self.assertRaises(expected_cls) as ctx:
                    _raise_for_error_status(status, '{}', self.SOURCE_TEXT, self.VOICE)
                self.assertIsInstance(ctx.exception, errors.ServiceRequestError)
