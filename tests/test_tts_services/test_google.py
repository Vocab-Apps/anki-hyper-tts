import copy
import base64
import unittest
from unittest import mock

from .base import TTSTests, logger
from hypertts_addon import constants
from hypertts_addon import context
from hypertts_addon import errors
from hypertts_addon import languages
from hypertts_addon import voice as voice_module


class TestGoogle(TTSTests):

    def test_google(self):
        service_name = 'Google'

        voice_list = self.manager.full_voice_list()
        google_voices = [voice for voice in voice_list if voice.service == 'Google']
        # print(voice_list)
        logger.info(f'found {len(google_voices)} voices for Google services')
        assert len(google_voices) > 300

        # pick a random en_US voice
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, 'Google', audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence')

        # french
        audio_language = languages.AudioLanguage.fr_FR
        selected_voice = self.pick_random_voice(voice_list, 'Google', audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'Je ne suis pas disponible.')

        # test ogg format
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, service_name, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence', voice_options={'format': 'ogg_opus'})

        # test Chirp voice
        audio_language = languages.AudioLanguage.en_US
        chirp_voices = [voice for voice in voice_list if voice.service == 'Google' and 'en-US-Chirp3-HD-Charon' in voice.voice_key['name']]
        self.assertEqual(len(chirp_voices), 1)
        chirp_voice = chirp_voices[0]
        self.verify_audio_output(chirp_voice, audio_language, 'This is the first sentence')

        # error checking
        # try a voice which doesn't exist
        selected_voice = self.pick_random_voice(voice_list, 'Google', languages.AudioLanguage.en_US)
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
            assert e.voice.service == 'Google'
            exception_caught = True
        assert exception_caught


class TestGoogleMp3Reencode(unittest.TestCase):
    """Mock tests: mp3 output requests lossless LINEAR16 and re-encodes locally.

    Google's native MP3 is a fixed ~32 kbps; we request LINEAR16 and re-encode
    at constants.AUDIO_MP3_ENCODE_BITRATE_KBPS so the user gets a better mp3.
    """

    def _voice(self):
        return voice_module.TtsVoice_v3(
            name='Test', voice_key={'name': 'en-US-Standard-A', 'language_code': 'en-US'},
            options={'speaking_rate': {'type': 'number', 'min': 0.25, 'max': 4.0, 'default': 1.0}},
            service='Google', gender=constants.Gender.Male,
            audio_languages=[languages.AudioLanguage.en_US], service_fee=constants.ServiceFee.paid)

    def _resp(self, raw_bytes):
        r = mock.Mock()
        r.status_code = 200
        r.json.return_value = {'audioContent': base64.b64encode(raw_bytes).decode()}
        return r

    def test_mp3_requests_linear16_and_reencodes(self):
        # pytest tests/test_tts_services/test_google.py -k 'test_mp3_requests_linear16_and_reencodes'
        from hypertts_addon.services.service_google import Google
        service = Google()
        service.configure({'api_key': 'fake_key'})

        with mock.patch('hypertts_addon.services.service_google.requests.post',
                        return_value=self._resp(b'RIFF....WAVE....')) as mock_post, \
             mock.patch('hypertts_addon.services.service_google.audio_utils.encode_wav_to_mp3',
                        return_value=b'MP3BYTES') as mock_encode:
            out = service.get_tts_audio('hello', self._voice(), {})

        self.assertEqual(mock_post.call_args.kwargs['json']['audioConfig']['audioEncoding'], 'LINEAR16')
        self.assertEqual(out, b'MP3BYTES')
        # the lossless WAV is handed to the encoder at the configured bitrate
        self.assertEqual(mock_encode.call_args.args[0], b'RIFF....WAVE....')
        self.assertEqual(mock_encode.call_args.args[1], constants.AUDIO_MP3_ENCODE_BITRATE_KBPS)

    def test_ogg_opus_returned_directly(self):
        # pytest tests/test_tts_services/test_google.py -k 'test_ogg_opus_returned_directly'
        from hypertts_addon.services.service_google import Google
        service = Google()
        service.configure({'api_key': 'fake_key'})

        with mock.patch('hypertts_addon.services.service_google.requests.post',
                        return_value=self._resp(b'OGGDATA')) as mock_post, \
             mock.patch('hypertts_addon.services.service_google.audio_utils.encode_wav_to_mp3') as mock_encode:
            out = service.get_tts_audio('hi', self._voice(), {'format': 'ogg_opus'})

        self.assertEqual(mock_post.call_args.kwargs['json']['audioConfig']['audioEncoding'], 'OGG_OPUS')
        self.assertEqual(out, b'OGGDATA')
        self.assertFalse(mock_encode.called)


class TestGoogleCLT(TestGoogle):
    CONFIG_MODE = 'clt'
