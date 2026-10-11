import unittest
import unittest.mock as mock

from .base import TTSTests, logger
from hypertts_addon import errors
from hypertts_addon.languages import AudioLanguage
from hypertts_addon.services import service_vocalware


class TestVocalWare(TTSTests):

    def test_vocalware(self):
        # pytest tests/test_tts_services/ -k 'TestVocalWare and test_vocalware'
        service_name = 'VocalWare'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]
        assert len(service_voices) > 50

        # pick a random en_US voice
        self.random_voice_test(service_name, AudioLanguage.en_US, 'This is the first sentence')


class TestVocalWareCLT(TestVocalWare):
    CONFIG_MODE = 'clt'


class TestVocalWareErrorBody(unittest.TestCase):
    """VocalWare answers HTTP 200 with a plain text error body when it cannot synthesize
    (seen on the Wang and Miyu voices); that must surface as an error, not as an mp3 file."""

    def setUp(self):
        self.service = service_vocalware.VocalWare()
        self.service._config = {'secret_phrase': 'x', 'account_id': '1', 'api_id': '2'}
        self.voice = mock.Mock()
        self.voice.voice_key = {'engine_id': 2, 'language_id': 10, 'voice_id': 1}

    def mock_response(self, content):
        response = mock.Mock()
        response.status_code = 200
        response.content = content
        return response

    def test_408_error_body_raises_timeout_error(self):
        # pytest tests/test_tts_services/test_vocalware.py -k test_408_error_body_raises_timeout_error
        response = self.mock_response(b'Error: [408 Request Timeout] Unable to process')
        with mock.patch('requests.get', return_value=response) as get:
            with self.assertRaises(errors.ServiceTimeoutError) as ctx:
                self.service.get_tts_audio('hello', self.voice, {})
        self.assertTrue(ctx.exception.retryable)
        self.assertIn('408', str(ctx.exception))
        self.assertEqual(get.call_count, 1)

    def test_other_error_body_raises_unknown_service_error(self):
        # pytest tests/test_tts_services/test_vocalware.py -k test_other_error_body_raises_unknown_service_error
        response = self.mock_response(b'Error: [500 Something] Unable to process')
        with mock.patch('requests.get', return_value=response):
            with self.assertRaises(errors.UnknownServiceError):
                self.service.get_tts_audio('hello', self.voice, {})

    def test_mp3_body_is_returned(self):
        # pytest tests/test_tts_services/test_vocalware.py -k test_mp3_body_is_returned
        response = self.mock_response(b'ID3\x03\x00audio')
        with mock.patch('requests.get', return_value=response):
            self.assertEqual(self.service.get_tts_audio('hello', self.voice, {}), b'ID3\x03\x00audio')
