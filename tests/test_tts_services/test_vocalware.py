from .base import TTSTests, logger
from hypertts_addon.languages import AudioLanguage


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
