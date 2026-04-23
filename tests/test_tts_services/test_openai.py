import unittest
import unittest.mock as mock

import pytest

from .base import TTSTests, logger
from hypertts_addon import languages
from hypertts_addon import errors
from hypertts_addon.languages import AudioLanguage
from hypertts_addon.services import service_openai


class TestOpenAI(TTSTests):

    def test_openai_english(self):
        # pytest tests/test_tts_services/ -k 'TestOpenAI and test_openai_english'
        service_name = 'OpenAI'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]
        assert len(service_voices) > 5

        # pick a random en_US voice
        self.random_voice_test(service_name, AudioLanguage.en_US, 'This is the first sentence')

        # test ogg format
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, AudioLanguage.en_US, 'This is the first sentence', voice_options={'format': 'ogg_opus'})

    @pytest.mark.skip(reason="openai for non-english languages doesn't produce reliable results")
    def test_openai_french(self):
        self.random_voice_test('OpenAI', languages.AudioLanguage.fr_FR, 'Il va pleuvoir demain.')


class TestOpenAICLT(TestOpenAI):
    CONFIG_MODE = 'clt'


class TestOpenAIErrorHandling(unittest.TestCase):

    def setUp(self):
        self.service = service_openai.OpenAI()
        self.service._config = {'api_key': 'fake_key'}
        self.service.api_key = 'fake_key'

        self.mock_voice = mock.Mock()
        self.mock_voice.voice_key = {'name': 'alloy'}
        self.mock_voice.options = {
            'speed': {'default': 1.0},
            'model': {'default': 'tts-1'},
            'instructions': {'default': ''},
        }

    def test_openai_rate_limit_429(self):
        # pytest tests/test_tts_services/test_openai.py -k 'test_openai_rate_limit_429'
        mock_response = mock.Mock()
        mock_response.status_code = 429
        mock_response.text = 'Too Many Requests'
        mock_response.headers = {}

        with mock.patch('requests.post', return_value=mock_response):
            with self.assertRaises(errors.RateLimitError) as context:
                self.service.get_tts_audio('hello', self.mock_voice, {})

            self.assertIsInstance(context.exception, errors.TransientError)
            self.assertIn('429', str(context.exception))

    def test_openai_unauthorized_401(self):
        # pytest tests/test_tts_services/test_openai.py -k 'test_openai_unauthorized_401'
        mock_response = mock.Mock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        mock_response.headers = {}

        with mock.patch('requests.post', return_value=mock_response):
            with self.assertRaises(errors.ServicePermissionError) as context:
                self.service.get_tts_audio('hello', self.mock_voice, {})

            self.assertIsInstance(context.exception, errors.PermanentError)
            self.assertIn('401', str(context.exception))
