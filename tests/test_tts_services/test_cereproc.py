from .base import TTSTests, logger
from hypertts_addon.languages import AudioLanguage


class TestCereProc(TTSTests):

    def test_cereproc(self):
        # pytest tests/test_tts_services/ -k 'TestCereProc and test_cereproc'
        service_name = 'CereProc'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]
        assert len(service_voices) > 50

        # pick a random en_US voice
        self.random_voice_test(service_name, AudioLanguage.en_GB, 'This is the first sentence')


class TestCereProcCLT(TestCereProc):
    CONFIG_MODE = 'clt'
