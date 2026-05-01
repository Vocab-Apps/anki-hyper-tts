import random
import unittest
import pytest

from .base import TTSTests, logger
from hypertts_addon import constants
from hypertts_addon import context
from hypertts_addon import errors
from hypertts_addon import languages
from hypertts_addon.languages import AudioLanguage


class TestElevenLabs(TTSTests):

    def test_elevenlabs_english(self):
        # pytest tests/test_tts_services/ -k 'TestElevenLabs and test_elevenlabs_english'
        service_name = 'ElevenLabs'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]
        assert len(service_voices) > 5

        # pick a random en_US voice
        self.random_voice_test(service_name, AudioLanguage.en_US, 'This is the first sentence')

    def test_elevenlabs_with_voice_settings(self):
        # pytest tests/test_tts_services/ -k 'TestElevenLabs and test_elevenlabs_with_voice_settings'
        service_name = 'ElevenLabs'
        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name and AudioLanguage.en_US in voice.audio_languages]
        assert len(service_voices) > 0
        selected_voice = random.choice(service_voices)
        voice_options = {'style': 0.5, 'speed': 0.9, 'use_speaker_boost': 'true'}
        self.verify_audio_output(selected_voice, AudioLanguage.en_US, 'This is the first sentence', voice_options=voice_options)

    def test_elevenlabs_ogg_format(self):
        # pytest tests/test_tts_services/ -k 'TestElevenLabs and test_elevenlabs_ogg_format'
        service_name = 'ElevenLabs'
        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name
                          and AudioLanguage.en_US in voice.audio_languages
                          and 'format' in voice.options]
        if not service_voices:
            raise unittest.SkipTest('No ElevenLabs voices with format option found')
        selected_voice = random.choice(service_voices)
        self.verify_audio_output(selected_voice, AudioLanguage.en_US, 'This is the first sentence', voice_options={'format': 'ogg_opus'})

    def test_elevenlabs_english_all_voices_alice(self):
        # pytest tests/test_tts_services/ -k 'TestElevenLabs and test_elevenlabs_english_all_voices_alice'
        service_name = 'ElevenLabs'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name and AudioLanguage.en_US in voice.audio_languages]
        charlotte_voices = [voice for voice in service_voices if 'Alice' in voice.name]
        # basically we are testing that all the ElevenLabs models are working, there should be 4 or them
        self.assertGreaterEqual(len(charlotte_voices), 4)
        self.assertLessEqual(len(charlotte_voices), 10)
        for voice in charlotte_voices:
            self.verify_audio_output(voice, AudioLanguage.en_US, 'This is the first sentence')

    @pytest.mark.skip(reason="elevenlabs for non-english languages doesn't produce reliable results")
    def test_elevenlabs_french(self):
        self.random_voice_test('ElevenLabs', languages.AudioLanguage.fr_FR, 'Il va pleuvoir demain.')

    def test_elevenlabs_japanese(self):
        self.random_voice_test('ElevenLabs', languages.AudioLanguage.ja_JP, 'おはようございます')

    @pytest.mark.skip(reason="elevenlabs for non-english languages doesn't produce reliable results")
    def test_elevenlabs_chinese(self):
        self.random_voice_test('ElevenLabs', languages.AudioLanguage.zh_CN, '赚钱')

    def test_elevenlabs_custom(self):
        # pytest tests/test_tts_services/ -k 'TestElevenLabs and test_elevenlabs_custom'

        service_name = 'ElevenLabsCustom'
        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()

        # pick a random en_US voice
        self.random_voice_test(service_name, AudioLanguage.en_US, 'This is the first sentence')

    def test_elevenlabs_with_language_code(self):
        # pytest tests/test_tts_services/ -k 'TestElevenLabs and test_elevenlabs_with_language_code'
        service_name = 'ElevenLabs'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name and AudioLanguage.en_US in voice.audio_languages]

        # Find voices that use Turbo v2.5 or Flash v2.5 models (which support language_code)
        compatible_voices = [voice for voice in service_voices
                           if voice.voice_key['model_id'] in ['eleven_turbo_v2_5', 'eleven_flash_v2_5']]

        if len(compatible_voices) == 0:
            raise unittest.SkipTest('No ElevenLabs voices with Turbo v2.5 or Flash v2.5 models found')

        # Pick a random voice from the compatible ones
        selected_voice = random.choice(compatible_voices)

        logger.info(f'Testing language_code with voice: {selected_voice.name} using model: {selected_voice.voice_key["model_id"]}')

        # Test with English language code
        voice_options = {'language_code': 'en'}
        self.verify_audio_output(selected_voice, AudioLanguage.en_US, 'Hello world', voice_options=voice_options)

        # Test with empty language code (should be omitted from request)
        voice_options = {'language_code': ''}
        self.verify_audio_output(selected_voice, AudioLanguage.en_US, 'Hello world', voice_options=voice_options)

        # Test without language_code option (should use default)
        voice_options = {}
        self.verify_audio_output(selected_voice, AudioLanguage.en_US, 'Hello world', voice_options=voice_options)

    def test_elevenlabs_custom_with_language_code(self):
        # pytest tests/test_tts_services/ -k 'TestElevenLabs and test_elevenlabs_custom_with_language_code'
        service_name = 'ElevenLabsCustom'

        if self.manager.get_service(service_name).enabled == False:
            logger.warning(f'service {service_name} not enabled, skipping')
            raise unittest.SkipTest(f'service {service_name} not enabled, skipping')

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name and AudioLanguage.en_US in voice.audio_languages]

        if len(service_voices) == 0:
            raise unittest.SkipTest('No ElevenLabsCustom voices found')

        # Find voices that use Turbo v2.5 or Flash v2.5 models (which support language_code)
        compatible_voices = [voice for voice in service_voices
                           if voice.voice_key['model_id'] in ['eleven_turbo_v2_5', 'eleven_flash_v2_5']]

        if len(compatible_voices) == 0:
            raise unittest.SkipTest('No ElevenLabsCustom voices with Turbo v2.5 or Flash v2.5 models found')

        # Pick a random voice from the compatible ones
        selected_voice = random.choice(compatible_voices)

        logger.info(f'Testing ElevenLabsCustom language_code with voice: {selected_voice.name} using model: {selected_voice.voice_key["model_id"]}')

        # Test with English language code
        voice_options = {'language_code': 'en'}
        self.verify_audio_output(selected_voice, AudioLanguage.en_US, 'Hello world', voice_options=voice_options)

        # Test with empty language code (should be omitted from request)
        voice_options = {'language_code': ''}
        self.verify_audio_output(selected_voice, AudioLanguage.en_US, 'Hello world', voice_options=voice_options)

        # Test without language_code option (should use default)
        voice_options = {}
        self.verify_audio_output(selected_voice, AudioLanguage.en_US, 'Hello world', voice_options=voice_options)

    @pytest.mark.skip(reason="doesn't seem to work reliably, not required")
    def test_elevenlabs_unsupported_language_code_error(self):
        # pytest tests/test_tts_services/ -k 'TestElevenLabs and test_elevenlabs_unsupported_language_code_error'
        service_name = 'ElevenLabs'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name and AudioLanguage.en_US in voice.audio_languages]

        # Find a monolingual voice (which doesn't support language_code)
        monolingual_voice = None
        for voice in service_voices:
            if 'monolingual' in voice.voice_key['model_id']:
                monolingual_voice = voice
                break

        if monolingual_voice is None:
            raise unittest.SkipTest('No ElevenLabs monolingual voice found for error testing')

        logger.info(f'Testing language_code error with monolingual voice: {monolingual_voice.name} using model: {monolingual_voice.voice_key["model_id"]}')

        # Test with language_code provided to a model that doesn't support it
        voice_options = {'language_code': 'en'}

        # This should raise a RequestError with a meaningful message
        exception_caught = False
        try:
            self.manager.get_tts_audio('Hello world', monolingual_voice, voice_options,
                context.AudioRequestContext(constants.AudioRequestReason.batch))
        except errors.RequestError as e:
            exception_caught = True
            error_message = str(e)
            # Verify the error message contains information about language_code not being supported
            self.assertIn('language code parameter', error_message.lower())
            self.assertIn('does not support', error_message.lower())
            logger.info(f'Got expected error message: {error_message}')

        self.assertTrue(exception_caught, 'Expected RequestError was not raised when using language_code with monolingual model')


class TestElevenLabsQuotaError(unittest.TestCase):
    """Mock tests for ElevenLabs quota exceeded error handling."""

    QUOTA_EXCEEDED_JSON = {
        "detail": {
            "status": "quota_exceeded",
            "message": "This request exceeds your quota of 10000. You have 0 credits remaining, while 43 credits are required for this request."
        }
    }

    PAID_PLAN_REQUIRED_JSON = {
        "detail": {
            "type": "payment_required",
            "code": "paid_plan_required",
            "message": "Free users cannot use library voices via the API. Please upgrade your subscription to use this voice.",
            "status": "payment_required"
        }
    }
    PAID_PLAN_REQUIRED_TEXT = '{"detail":{"type":"payment_required","code":"paid_plan_required","message":"Free users cannot use library voices via the API. Please upgrade your subscription to use this voice.","status":"payment_required"}}'

    def _make_mock_voice(self, service_name):
        from hypertts_addon import voice as voice_module
        return voice_module.TtsVoice_v3(
            name='Test Voice',
            voice_key={'voice_id': 'test_id', 'model_id': 'eleven_monolingual_v1'},
            options={
                'stability': {'type': 'number', 'min': 0.0, 'max': 1.0, 'default': 0.5},
                'similarity_boost': {'type': 'number', 'min': 0.0, 'max': 1.0, 'default': 0.75},
            },
            service=service_name,
            gender=constants.Gender.Male,
            audio_languages=[AudioLanguage.en_US],
            service_fee=constants.ServiceFee.paid,
        )

    def _make_quota_response(self):
        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = self.QUOTA_EXCEEDED_JSON
        mock_response.text = '{"detail":{"status":"quota_exceeded","message":"This request exceeds your quota of 10000. You have 0 credits remaining, while 43 credits are required for this request."}}'
        return mock_response

    def _make_401_no_json_response(self):
        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.side_effect = ValueError("No JSON")
        mock_response.text = 'Unauthorized'
        return mock_response

    def _make_paid_plan_required_response(self):
        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.status_code = 402
        mock_response.json.return_value = self.PAID_PLAN_REQUIRED_JSON
        mock_response.text = self.PAID_PLAN_REQUIRED_TEXT
        return mock_response

    def test_elevenlabs_quota_exceeded_raises_permission_error(self):
        # pytest tests/test_tts_services/test_elevenlabs.py -k 'test_elevenlabs_quota_exceeded_raises_permission_error'
        from unittest.mock import patch
        from hypertts_addon.services.service_elevenlabs import ElevenLabs

        service = ElevenLabs()
        service.configure({'api_key': 'fake_key'})
        mock_voice = self._make_mock_voice('ElevenLabs')

        with patch('hypertts_addon.services.service_elevenlabs.requests.post', return_value=self._make_quota_response()):
            with self.assertRaises(errors.ServicePermissionError) as ctx:
                service.get_tts_audio('Hello', mock_voice, {})
            self.assertIn('401', ctx.exception.error_message)
            self.assertIn('quota_exceeded', ctx.exception.error_message)

    def test_elevenlabscustom_quota_exceeded_raises_permission_error(self):
        # pytest tests/test_tts_services/test_elevenlabs.py -k 'test_elevenlabscustom_quota_exceeded_raises_permission_error'
        from unittest.mock import patch
        from hypertts_addon.services.service_elevenlabscustom import ElevenLabsCustom

        service = ElevenLabsCustom()
        service.configure({'api_key': 'fake_key'})
        mock_voice = self._make_mock_voice('ElevenLabsCustom')

        with patch('hypertts_addon.services.service_elevenlabscustom.requests.post', return_value=self._make_quota_response()):
            with self.assertRaises(errors.ServicePermissionError) as ctx:
                service.get_tts_audio('Hello', mock_voice, {})
            self.assertIn('401', ctx.exception.error_message)
            self.assertIn('quota_exceeded', ctx.exception.error_message)

    def test_elevenlabs_401_no_json_raises_permission_error(self):
        # pytest tests/test_tts_services/test_elevenlabs.py -k 'test_elevenlabs_401_no_json_raises_permission_error'
        from unittest.mock import patch
        from hypertts_addon.services.service_elevenlabs import ElevenLabs

        service = ElevenLabs()
        service.configure({'api_key': 'fake_key'})
        mock_voice = self._make_mock_voice('ElevenLabs')

        with patch('hypertts_addon.services.service_elevenlabs.requests.post', return_value=self._make_401_no_json_response()):
            with self.assertRaises(errors.ServicePermissionError) as ctx:
                service.get_tts_audio('Hello', mock_voice, {})
            self.assertIn('401', ctx.exception.error_message)
            self.assertIn('Unauthorized', ctx.exception.error_message)

    def test_elevenlabs_paid_plan_required_raises_permission_error(self):
        # pytest tests/test_tts_services/test_elevenlabs.py -k 'test_elevenlabs_paid_plan_required_raises_permission_error'
        from unittest.mock import patch
        from hypertts_addon.services.service_elevenlabs import ElevenLabs

        service = ElevenLabs()
        service.configure({'api_key': 'fake_key'})
        mock_voice = self._make_mock_voice('ElevenLabs')

        with patch('hypertts_addon.services.service_elevenlabs.requests.post', return_value=self._make_paid_plan_required_response()):
            with self.assertRaises(errors.ServicePermissionError) as ctx:
                service.get_tts_audio('Hello', mock_voice, {})
            self.assertIn('402', ctx.exception.error_message)
            self.assertIn('paid_plan_required', ctx.exception.error_message)

    def test_elevenlabscustom_paid_plan_required_raises_permission_error(self):
        # pytest tests/test_tts_services/test_elevenlabs.py -k 'test_elevenlabscustom_paid_plan_required_raises_permission_error'
        from unittest.mock import patch
        from hypertts_addon.services.service_elevenlabscustom import ElevenLabsCustom

        service = ElevenLabsCustom()
        service.configure({'api_key': 'fake_key'})
        mock_voice = self._make_mock_voice('ElevenLabsCustom')

        with patch('hypertts_addon.services.service_elevenlabscustom.requests.post', return_value=self._make_paid_plan_required_response()):
            with self.assertRaises(errors.ServicePermissionError) as ctx:
                service.get_tts_audio('Hello', mock_voice, {})
            self.assertIn('402', ctx.exception.error_message)
            self.assertIn('paid_plan_required', ctx.exception.error_message)

    def test_elevenlabs_other_error_raises_request_error(self):
        # pytest tests/test_tts_services/test_elevenlabs.py -k 'test_elevenlabs_other_error_raises_request_error'
        from unittest.mock import patch, MagicMock
        from hypertts_addon.services.service_elevenlabs import ElevenLabs

        service = ElevenLabs()
        service.configure({'api_key': 'fake_key'})
        mock_voice = self._make_mock_voice('ElevenLabs')

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("No JSON")
        mock_response.text = 'Internal Server Error'

        with patch('hypertts_addon.services.service_elevenlabs.requests.post', return_value=mock_response):
            with self.assertRaises(errors.RequestError):
                service.get_tts_audio('Hello', mock_voice, {})


class TestElevenLabsCLT(TestElevenLabs):
    CONFIG_MODE = 'clt'
