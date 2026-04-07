import copy

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


class TestGoogleCLT(TestGoogle):
    CONFIG_MODE = 'clt'
