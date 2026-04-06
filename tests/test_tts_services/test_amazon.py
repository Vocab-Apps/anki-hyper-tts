from .base import TTSTests
from hypertts_addon import languages
from hypertts_addon.languages import AudioLanguage


class TestAmazon(TTSTests):

    def test_amazon(self):
        # pytest tests/test_tts_services/ -k 'TestAmazon and test_amazon'
        service_name = 'Amazon'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]
        assert len(service_voices) > 50

        # pick a random en_US voice
        self.random_voice_test(service_name, AudioLanguage.en_US, 'This is the first sentence')

        # test ogg format
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, AudioLanguage.en_US, 'This is the first sentence', voice_options={'format': 'ogg_vorbis'})


class TestAmazonCLT(TestAmazon):
    CONFIG_MODE = 'clt'
