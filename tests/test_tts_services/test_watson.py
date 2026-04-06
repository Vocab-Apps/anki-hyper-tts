from .base import TTSTests, logger
from hypertts_addon.languages import AudioLanguage


class TestWatson(TTSTests):

    def test_watson(self):
        # pytest tests/test_tts_services/ -k 'TestWatson and test_watson'
        service_name = 'Watson'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]
        assert len(service_voices) > 50

        # pick a random en_US voice
        self.random_voice_test(service_name, AudioLanguage.en_US, 'This is the first sentence')


class TestWatsonCLT(TestWatson):
    CONFIG_MODE = 'clt'
