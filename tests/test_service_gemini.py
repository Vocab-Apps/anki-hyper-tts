import base64
import hashlib
import unittest
import unittest.mock as mock

import requests

from hypertts_addon import errors
from hypertts_addon import languages
from hypertts_addon.services import service_gemini


class TestGeminiService(unittest.TestCase):
    def setUp(self):
        self.service = service_gemini.Gemini()
        self.service.configure({
            'project_id': 'fake-project',
            'throttle_seconds': 0.0,
            'max_retries': 2,
            'retry_delay_seconds': 0.1,
        })
        self.voice = next(
            voice_entry for voice_entry in self.service.voice_list()
            if voice_entry.name == 'Kore' and voice_entry.voice_key['language_code'] == 'cmn-tw'
        )

    def build_success_response(self, audio_bytes=b'FAKE_MP3'):
        success_response = mock.Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            'audioContent': base64.b64encode(audio_bytes).decode('ascii'),
        }
        return success_response

    def test_voice_list_contains_expected_catalog_and_taiwan_locale(self):
        voice_list = self.service.voice_list()

        self.assertEqual(
            len(voice_list),
            len(service_gemini.VOICE_NAMES) * len(service_gemini.SUPPORTED_VOICE_LOCALES),
        )
        self.assertEqual(self.voice.voice_key, {'voice_name': 'Kore', 'language_code': 'cmn-tw'})
        self.assertEqual(self.voice.audio_languages, [languages.AudioLanguage.zh_TW])
        self.assertEqual(self.voice.options['model']['default'], 'gemini-2.5-flash-tts')

    def test_configuration_ui_metadata_marks_service_as_cloud_tts(self):
        self.assertEqual(self.service.configuration_options(), {'project_id': str})
        self.assertEqual(self.service.configuration_display_name(), 'Gemini (Cloud TTS)')
        self.assertIn('Cloud Text-to-Speech Gemini-TTS', self.service.configuration_description())
        self.assertIn('Taiwan Mandarin', self.service.configuration_description())

    def test_normalize_voice_key_accepts_legacy_name_and_language_formats(self):
        self.assertEqual(
            self.service.normalize_voice_key({'name': 'Kore'}),
            {'voice_name': 'Kore'},
        )
        self.assertEqual(
            self.service.normalize_voice_key({'voice_name': 'Kore', 'language_code': 'cmn-TW'}),
            {'voice_name': 'Kore', 'language_code': 'cmn-tw'},
        )
        self.assertTrue(
            self.service.matches_voice_key(
                {'voice_name': 'Kore'},
                {'voice_name': 'Kore', 'language_code': 'en-us'},
            )
        )

    def test_build_payload_uses_selected_model_voice_and_locale(self):
        model, payload = self.service.build_payload('你好', self.voice, {
            'model': 'gemini-2.5-pro-tts',
            'instructions': 'Speak naturally in Taiwan Mandarin.',
        })

        self.assertEqual(model, 'gemini-2.5-pro-tts')
        self.assertEqual(payload['input']['text'], '你好')
        self.assertEqual(payload['input']['prompt'], 'Speak naturally in Taiwan Mandarin.')
        self.assertEqual(payload['voice']['languageCode'], 'cmn-tw')
        self.assertEqual(payload['voice']['name'], 'Kore')
        self.assertEqual(payload['voice']['modelName'], 'gemini-2.5-pro-tts')
        self.assertEqual(payload['audioConfig']['audioEncoding'], 'MP3')

    def test_build_request_headers_uses_bearer_token_and_project_header(self):
        with mock.patch.object(self.service, 'get_access_token', return_value='token-123'):
            headers = self.service.build_request_headers('Hello', self.voice)

        self.assertEqual(headers['Authorization'], 'Bearer token-123')
        self.assertEqual(headers['x-goog-user-project'], 'fake-project')
        self.assertEqual(headers['Content-Type'], 'application/json; charset=utf-8')

    def test_get_access_token_raises_when_gcloud_missing(self):
        with mock.patch('hypertts_addon.services.service_gemini.shutil.which', return_value=None):
            with self.assertRaises(errors.RequestError) as exception_context:
                self.service.get_access_token('Hello', self.voice)

        self.assertIn('gcloud CLI not found', str(exception_context.exception))

    def test_get_access_token_uses_gcloud_and_caches_value(self):
        completed = mock.Mock(returncode=0, stdout='token-123\n', stderr='')

        with mock.patch('hypertts_addon.services.service_gemini.shutil.which', return_value='/usr/bin/gcloud'):
            with mock.patch('hypertts_addon.services.service_gemini.subprocess.run', return_value=completed) as run_mock:
                first_token = self.service.get_access_token('Hello', self.voice)
                second_token = self.service.get_access_token('Hello', self.voice)

        self.assertEqual(first_token, 'token-123')
        self.assertEqual(second_token, 'token-123')
        run_mock.assert_called_once()

    def test_get_tts_audio_uses_mp3_response(self):
        success_response = self.build_success_response(audio_bytes=b'FAKE_MP3')

        with mock.patch.object(self.service, 'get_access_token', return_value='token-123'):
            with mock.patch('hypertts_addon.services.service_gemini.requests.post', return_value=success_response) as post_mock:
                audio = self.service.get_tts_audio('Hello there', self.voice, {})

        self.assertEqual(audio, b'FAKE_MP3')
        request_url = post_mock.call_args.args[0]
        request_headers = post_mock.call_args.kwargs['headers']
        self.assertEqual(request_url, 'https://texttospeech.googleapis.com/v1/text:synthesize')
        self.assertEqual(request_headers['Authorization'], 'Bearer token-123')
        self.assertEqual(request_headers['x-goog-user-project'], 'fake-project')

    def test_get_tts_audio_retries_and_honors_retry_after(self):
        rate_limit_response = mock.Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '7'}
        rate_limit_response.json.return_value = {
            'error': {
                'message': 'Rate limit exceeded'
            }
        }

        success_response = self.build_success_response()

        with mock.patch.object(self.service, 'get_access_token', return_value='token-123'):
            with mock.patch('hypertts_addon.services.service_gemini.time.sleep') as sleep_mock:
                with mock.patch('hypertts_addon.services.service_gemini.requests.post', side_effect=[rate_limit_response, success_response]) as post_mock:
                    audio = self.service.get_tts_audio('Hello there', self.voice, {'instructions': 'Speak warmly'})

        self.assertEqual(audio, b'FAKE_MP3')
        self.assertEqual(post_mock.call_count, 2)
        sleep_mock.assert_called_once_with(7.0)

    def test_get_tts_audio_retries_request_exception(self):
        success_response = self.build_success_response(audio_bytes=b'FAKE_MP3')

        with mock.patch.object(self.service, 'get_access_token', return_value='token-123'):
            with mock.patch('hypertts_addon.services.service_gemini.time.sleep') as sleep_mock:
                with mock.patch(
                    'hypertts_addon.services.service_gemini.requests.post',
                    side_effect=[requests.exceptions.ReadTimeout('timeout'), success_response],
                ) as post_mock:
                    audio = self.service.get_tts_audio('Hello there', self.voice, {})

        self.assertEqual(audio, b'FAKE_MP3')
        self.assertEqual(post_mock.call_count, 2)
        sleep_mock.assert_called_once_with(0.1)

    def test_get_tts_audio_refreshes_token_after_401(self):
        self.service.configure({
            'project_id': 'fake-project',
            'throttle_seconds': 0.0,
            'max_retries': 0,
            'retry_delay_seconds': 0.1,
        })
        unauthorized_response = mock.Mock()
        unauthorized_response.status_code = 401
        unauthorized_response.headers = {}
        unauthorized_response.json.return_value = {
            'error': {
                'message': 'Unauthenticated',
            }
        }
        success_response = self.build_success_response()

        with mock.patch.object(self.service, 'get_access_token', side_effect=['token-old', 'token-new']):
            with mock.patch('hypertts_addon.services.service_gemini.requests.post', side_effect=[unauthorized_response, success_response]) as post_mock:
                audio = self.service.get_tts_audio('Hello there', self.voice, {})

        self.assertEqual(audio, b'FAKE_MP3')
        self.assertEqual(post_mock.call_count, 2)
        self.assertEqual(post_mock.call_args_list[0].kwargs['headers']['Authorization'], 'Bearer token-old')
        self.assertEqual(post_mock.call_args_list[1].kwargs['headers']['Authorization'], 'Bearer token-new')

    def test_get_tts_audio_raises_request_error_after_second_401(self):
        self.service.configure({
            'project_id': 'fake-project',
            'throttle_seconds': 0.0,
            'max_retries': 0,
            'retry_delay_seconds': 0.1,
        })
        unauthorized_response = mock.Mock()
        unauthorized_response.status_code = 401
        unauthorized_response.headers = {}
        unauthorized_response.json.return_value = {
            'error': {
                'message': 'Unauthenticated',
            }
        }

        with mock.patch.object(self.service, 'get_access_token', side_effect=['token-old', 'token-new']):
            with mock.patch(
                'hypertts_addon.services.service_gemini.requests.post',
                side_effect=[unauthorized_response, unauthorized_response],
            ) as post_mock:
                with self.assertRaises(errors.RequestError) as exception_context:
                    self.service.get_tts_audio('Hello there', self.voice, {})

        self.assertIn('Unauthenticated', str(exception_context.exception))
        self.assertEqual(post_mock.call_count, 2)
        self.assertEqual(post_mock.call_args_list[0].kwargs['headers']['Authorization'], 'Bearer token-old')
        self.assertEqual(post_mock.call_args_list[1].kwargs['headers']['Authorization'], 'Bearer token-new')

    def test_get_tts_audio_respects_throttle(self):
        self.service.configure({
            'project_id': 'fake-project',
            'throttle_seconds': 0.25,
            'max_retries': 0,
            'retry_delay_seconds': 0.1,
        })
        success_response = self.build_success_response(audio_bytes=b'FAKE_MP3')

        with mock.patch.object(self.service, 'get_access_token', return_value='token-123'):
            with mock.patch('hypertts_addon.services.service_gemini.time.sleep') as sleep_mock:
                with mock.patch('hypertts_addon.services.service_gemini.requests.post', return_value=success_response):
                    audio = self.service.get_tts_audio('Hello there', self.voice, {})

        self.assertEqual(audio, b'FAKE_MP3')
        sleep_mock.assert_called_once_with(0.25)

    def test_get_tts_audio_raises_request_error_for_non_retryable_error(self):
        bad_response = mock.Mock()
        bad_response.status_code = 400
        bad_response.headers = {}
        bad_response.json.return_value = {
            'error': {
                'message': 'Bad request'
            }
        }

        with mock.patch.object(self.service, 'get_access_token', return_value='token-123'):
            with mock.patch('hypertts_addon.services.service_gemini.requests.post', return_value=bad_response):
                with self.assertRaises(errors.RequestError) as exception_context:
                    self.service.get_tts_audio('Hello there', self.voice, {})

        self.assertIn('Bad request', str(exception_context.exception))

    def test_get_tts_audio_raises_request_error_for_invalid_json_success_response(self):
        invalid_json_response = mock.Mock()
        invalid_json_response.status_code = 200
        invalid_json_response.json.side_effect = ValueError('not json')

        with mock.patch.object(self.service, 'get_access_token', return_value='token-123'):
            with mock.patch('hypertts_addon.services.service_gemini.requests.post', return_value=invalid_json_response):
                with self.assertRaises(errors.RequestError) as exception_context:
                    self.service.get_tts_audio('Hello there', self.voice, {})

        self.assertIn('invalid JSON response from Gemini Cloud TTS', str(exception_context.exception))

    def test_get_tts_audio_raises_request_error_for_missing_audio_payload(self):
        bad_response = mock.Mock()
        bad_response.status_code = 200
        bad_response.json.return_value = {}

        with mock.patch.object(self.service, 'get_access_token', return_value='token-123'):
            with mock.patch('hypertts_addon.services.service_gemini.requests.post', return_value=bad_response):
                with self.assertRaises(errors.RequestError) as exception_context:
                    self.service.get_tts_audio('Hello there', self.voice, {})

        self.assertIn('audio payload missing', str(exception_context.exception))

    def test_get_tts_audio_raises_request_error_for_invalid_base64_payload(self):
        bad_response = mock.Mock()
        bad_response.status_code = 200
        bad_response.json.return_value = {
            'audioContent': '%%%not-base64%%%',
        }

        with mock.patch.object(self.service, 'get_access_token', return_value='token-123'):
            with mock.patch('hypertts_addon.services.service_gemini.requests.post', return_value=bad_response):
                with self.assertRaises(errors.RequestError) as exception_context:
                    self.service.get_tts_audio('Hello there', self.voice, {})

        self.assertIn('invalid base64 audio payload', str(exception_context.exception))

    def test_audio_request_hash_changes_when_model_or_instructions_change(self):
        def get_hash_for_audio_request(source_text, voice_id, options):
            combined_data = {
                'source_text': source_text,
                'voice_id': voice_id,
                'options': options,
            }
            return hashlib.sha224(str(combined_data).encode('utf-8')).hexdigest()

        default_hash = get_hash_for_audio_request('Hello there', self.voice.voice_id, {
            'model': 'gemini-2.5-pro-tts',
            'instructions': '',
            'format': 'mp3',
        })
        instructions_hash = get_hash_for_audio_request('Hello there', self.voice.voice_id, {
            'model': 'gemini-2.5-pro-tts',
            'instructions': 'Natural and clear.',
            'format': 'mp3',
        })
        model_hash = get_hash_for_audio_request('Hello there', self.voice.voice_id, {
            'model': 'gemini-2.5-flash-tts',
            'instructions': '',
            'format': 'mp3',
        })

        self.assertNotEqual(default_hash, instructions_hash)
        self.assertNotEqual(default_hash, model_hash)
        self.assertNotEqual(instructions_hash, model_hash)


if __name__ == '__main__':
    unittest.main()
