import copy
import datetime
import random
import unittest
from unittest import mock

from .base import TTSTests, logger
from hypertts_addon import constants
from hypertts_addon import context
from hypertts_addon import errors
from hypertts_addon import languages
from hypertts_addon.languages import AudioLanguage
from hypertts_addon import voice as voice_module
from hypertts_addon.services import service_azure


class TestAzure(TTSTests):

    def test_azure(self):
        service_name = 'Azure'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]
        assert len(service_voices) > 300

        # pick a random en_US voice
        self.random_voice_test(service_name, AudioLanguage.en_US, self.ENGLISH_INPUT_TEXT)

        # french
        self.random_voice_test(service_name, AudioLanguage.fr_FR, 'Je ne suis pas disponible.')

        # test ogg format
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, AudioLanguage.en_US, self.ENGLISH_INPUT_TEXT, voice_options={'format': 'ogg_opus'})

        # error checking
        # try a voice which doesn't exist
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        selected_voice = copy.copy(selected_voice)
        voice_key = copy.copy(selected_voice.voice_key)
        voice_key['name'] = 'non existent'

        altered_voice = voice_module.TtsVoice_v3('non existent',
                                                 voice_key,
                                                 selected_voice.options,
                                                 service_name,
                                                 selected_voice.gender,
                                                 [languages.AudioLanguage.en_US],
                                                 constants.ServiceFee.paid)

        exception_caught = False
        try:
            audio_data = self.manager.get_tts_audio('This is the second sentence', altered_voice, {},
                context.AudioRequestContext(constants.AudioRequestReason.batch))
        except (errors.RequestError, errors.ServiceRequestError) as e:
            assert e.source_text == 'This is the second sentence'
            assert e.voice.service == service_name
            exception_caught = True
        assert exception_caught

    def test_azure_dragonhd_parameters(self):
        # pytest tests/test_tts_services/ -k 'TestAzure and test_azure_dragonhd_parameters'
        service_name = 'Azure'
        voice_list = self.manager.full_voice_list()
        dragonhd_voices = [v for v in voice_list if v.service == service_name
                           and 'DragonHD' in v.voice_key.get('name', '')
                           and AudioLanguage.en_US in v.audio_languages]
        if len(dragonhd_voices) == 0:
            raise unittest.SkipTest('No Azure DragonHD voices found')
        selected_voice = random.choice(dragonhd_voices)
        self.verify_audio_output(selected_voice, AudioLanguage.en_US, self.ENGLISH_INPUT_TEXT,
                                 voice_options={'temperature': 0.5, 'top_p': 0.5})

    def test_azure_style(self):
        # pytest tests/test_tts_services/ -k 'TestAzure and test_azure_style'
        service_name = 'Azure'
        voice_list = self.manager.full_voice_list()
        style_voices = [v for v in voice_list if v.service == service_name
                        and 'style' in v.options
                        and len(v.options['style'].get('values', [])) > 1
                        and AudioLanguage.en_US in v.audio_languages]
        if len(style_voices) == 0:
            raise unittest.SkipTest('No Azure voices with style found')
        selected_voice = random.choice(style_voices)
        styles = [s for s in selected_voice.options['style']['values'] if s != '']
        voice_options = {'style': styles[0], 'styledegree': 1.5}
        self.verify_audio_output(selected_voice, AudioLanguage.en_US, self.ENGLISH_INPUT_TEXT, voice_options=voice_options)


    def test_azure_401_raises_permission_error(self):
        # pytest tests/test_tts_services/ -k 'TestAzure and test_azure_401_raises_permission_error'
        azure_service = service_azure.Azure()
        azure_service.configure({'api_key': 'dummy_key', 'region': 'eastus'})
        azure_service.access_token = 'dummy_token'
        azure_service.access_token_timestamp = datetime.datetime.now()

        azure_voices = [v for v in azure_service.voice_list() if AudioLanguage.en_US in v.audio_languages]
        selected_voice = azure_voices[0]

        mock_response = mock.Mock()
        mock_response.status_code = 401
        mock_response.reason = 'Unauthorized'
        mock_response.text = '{"error": "Invalid subscription key"}'

        with mock.patch('hypertts_addon.services.service_azure.requests.post', return_value=mock_response):
            with self.assertRaises(errors.ServicePermissionError) as cm:
                azure_service.get_tts_audio('hello', selected_voice, {})

        self.assertEqual(cm.exception.source_text, 'hello')
        self.assertEqual(cm.exception.voice.service, 'Azure')
        self.assertIn('401', cm.exception.error_message)
        self.assertIn('Invalid subscription key', cm.exception.error_message)


class TestAzureCLT(TestAzure):
    CONFIG_MODE = 'clt'


class TestAzureChosenLanguage(unittest.TestCase):
    """a multilingual Azure voice is told the chosen language with <lang xml:lang>"""

    def setUp(self):
        self.service = service_azure.Azure()
        self.service.configure({'api_key': 'dummy_key', 'region': 'eastus'})
        self.service.access_token = 'dummy_token'
        self.service.access_token_timestamp = datetime.datetime.now()
        self.jenny = [v for v in self.service.voice_list() if 'JennyMultilingualNeural' in v.voice_key['name']][0]

    def sent_ssml(self, voice):
        response = mock.Mock(status_code=400, reason='Bad Request', text='bad request', headers={})
        with mock.patch('hypertts_addon.services.service_azure.requests.post', return_value=response) as post:
            with self.assertRaises(errors.HyperTTSError):
                self.service.get_tts_audio('¿Dónde está la biblioteca?', voice, {})
        return post.call_args.kwargs['data'].decode('utf-8')

    def test_chosen_language_wraps_the_text_in_lang(self):
        jenny_mexico = [v for v in voice_module.expand_languages(self.jenny) if v.audio_languages == [AudioLanguage.es_MX]][0]
        ssml = self.sent_ssml(jenny_mexico)
        self.assertIn('<lang xml:lang="es-MX">¿Dónde está la biblioteca?</lang>', ssml)
        self.assertIn('<voice name="Microsoft Server Speech Text to Speech Voice (en-US, JennyMultilingualNeural)"', ssml)

    def test_multilingual_voices_can_be_told_a_language(self):
        self.assertTrue(self.service.can_send_audio_language(self.jenny))

    def test_multilingual_voice_without_a_chosen_language_has_no_lang(self):
        self.assertNotIn('<lang', self.sent_ssml(self.jenny))

    def test_locale_is_the_name_azure_gives_a_multilingual_voice_language(self):
        self.assertEqual(self.service.get_locale(AudioLanguage.es_MX), 'es-MX')
        self.assertEqual(self.service.get_locale(AudioLanguage.sr_RS), 'sr-RS')
        self.assertEqual(self.service.get_locale(AudioLanguage.zh_CN_shaanxi), 'zh-CN-shaanxi')

    def test_chosen_language_sits_inside_the_voice_style_and_rate(self):
        import xml.etree.ElementTree as ET
        styled = [v for v in self.service.voice_list() if len(v.audio_languages) > 1 and 'style' in v.options][0]
        styled_mexico = [v for v in voice_module.expand_languages(styled) if v.audio_languages == [AudioLanguage.es_MX]][0]
        response = mock.Mock(status_code=400, reason='Bad Request', text='bad request', headers={})
        with mock.patch('hypertts_addon.services.service_azure.requests.post', return_value=response) as post:
            with self.assertRaises(errors.HyperTTSError):
                self.service.get_tts_audio('¿Dónde está la biblioteca?', styled_mexico, {'rate': 1.5, 'style': 'whispering'})
        ns = {'s': 'https://www.w3.org/2001/10/synthesis', 'mstts': 'https://www.w3.org/2001/mstts'}
        speak = ET.fromstring(post.call_args.kwargs['data'].decode('utf-8'))
        lang = speak.find('s:voice/mstts:express-as/s:prosody/s:lang', ns)
        self.assertIsNotNone(lang, 'voice > express-as > prosody > lang')
        self.assertEqual(lang.get('{http://www.w3.org/XML/1998/namespace}lang'), 'es-MX')
        self.assertEqual(lang.text, '¿Dónde está la biblioteca?')
        self.assertEqual(speak.find('s:voice/mstts:express-as/s:prosody', ns).get('rate'), '1.5')
