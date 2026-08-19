import base64
import unittest
import unittest.mock as mock

from .base import TTSTests, logger
from hypertts_addon import languages
from hypertts_addon import errors
from hypertts_addon import options
from hypertts_addon.languages import AudioLanguage
from hypertts_addon.services import service_mistral


class TestMistral(TTSTests):

    def test_mistral_english(self):
        # pytest tests/test_tts_services/ -k 'TestMistral and test_mistral_english'
        service_name = 'Mistral'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]
        assert len(service_voices) >= 5

        self.random_voice_test(service_name, AudioLanguage.en_US, 'This is the first sentence')

    def test_mistral_french(self):
        # pytest tests/test_tts_services/ -k 'TestMistral and test_mistral_french'
        self.random_voice_test('Mistral', AudioLanguage.fr_FR, 'Il va pleuvoir demain.')


class TestMistralErrorHandling(unittest.TestCase):

    def setUp(self):
        self.service = service_mistral.Mistral()
        self.service._config = {'api_key': 'fake_key'}
        self.service.api_key = 'fake_key'

        self.mock_voice = mock.Mock()
        self.mock_voice.voice_key = {'voice_id': 'casual_male'}
        self.mock_voice.options = {
            'model': {'default': 'voxtral-mini-tts-2603'},
        }

    def _mock_response(self, status_code, text='', headers=None, content=b''):
        response = mock.Mock()
        response.status_code = status_code
        response.text = text
        response.headers = headers or {}
        response.content = content
        return response

    def test_mistral_rate_limit_429(self):
        # pytest tests/test_tts_services/test_mistral.py -k 'test_mistral_rate_limit_429'
        response = self._mock_response(429, 'Too Many Requests')
        with mock.patch('requests.post', return_value=response):
            with self.assertRaises(errors.RateLimitError) as ctx:
                self.service.get_tts_audio('hello', self.mock_voice, {})
            self.assertIsInstance(ctx.exception, errors.TransientError)
            self.assertIn('429', str(ctx.exception))

    def test_mistral_unauthorized_401(self):
        # pytest tests/test_tts_services/test_mistral.py -k 'test_mistral_unauthorized_401'
        response = self._mock_response(401, 'Unauthorized')
        with mock.patch('requests.post', return_value=response):
            with self.assertRaises(errors.ServicePermissionError) as ctx:
                self.service.get_tts_audio('hello', self.mock_voice, {})
            self.assertIsInstance(ctx.exception, errors.PermanentError)
            self.assertIn('401', str(ctx.exception))

    def test_mistral_forbidden_403(self):
        # pytest tests/test_tts_services/test_mistral.py -k 'test_mistral_forbidden_403'
        response = self._mock_response(403, 'Content policy violation')
        with mock.patch('requests.post', return_value=response):
            with self.assertRaises(errors.ServicePermissionError) as ctx:
                self.service.get_tts_audio('hello', self.mock_voice, {})
            self.assertIsInstance(ctx.exception, errors.PermanentError)
            self.assertIn('403', str(ctx.exception))

    def test_mistral_bad_request_400(self):
        # pytest tests/test_tts_services/test_mistral.py -k 'test_mistral_bad_request_400'
        response = self._mock_response(400, '{"error": "Invalid voice"}')
        with mock.patch('requests.post', return_value=response):
            with self.assertRaises(errors.ServiceInputError) as ctx:
                self.service.get_tts_audio('hello', self.mock_voice, {})
            self.assertIsInstance(ctx.exception, errors.PermanentError)
            self.assertIn('400', str(ctx.exception))

    def test_mistral_success_json_envelope(self):
        # pytest tests/test_tts_services/test_mistral.py -k 'test_mistral_success_json_envelope'
        audio_bytes = b'ID3-fake-mp3-payload'
        payload = {'audio_data': base64.b64encode(audio_bytes).decode('ascii')}
        response = self._mock_response(200, headers={'Content-Type': 'application/json'})
        response.json = mock.Mock(return_value=payload)

        with mock.patch('requests.post', return_value=response):
            result = self.service.get_tts_audio('hello', self.mock_voice, {})

        self.assertEqual(result, audio_bytes)

    def test_mistral_success_raw_audio_response(self):
        # pytest tests/test_tts_services/test_mistral.py -k 'test_mistral_success_raw_audio_response'
        audio_bytes = b'ID3-fake-mp3-payload'
        response = self._mock_response(
            200, headers={'Content-Type': 'audio/mpeg'}, content=audio_bytes
        )

        with mock.patch('requests.post', return_value=response):
            result = self.service.get_tts_audio('hello', self.mock_voice, {})

        self.assertEqual(result, audio_bytes)

    def test_mistral_unsupported_audio_format(self):
        # pytest tests/test_tts_services/test_mistral.py -k 'test_mistral_unsupported_audio_format'
        # ogg_opus must fail early; Mistral returns raw Opus (no Ogg container),
        # which HyperTTS's audio verification cannot recognise.
        with self.assertRaises(errors.ServiceInputError) as ctx:
            self.service.get_tts_audio(
                'hello',
                self.mock_voice,
                {options.AUDIO_FORMAT_PARAMETER: options.AudioFormat.ogg_opus.name},
            )
        self.assertIsInstance(ctx.exception, errors.PermanentError)
