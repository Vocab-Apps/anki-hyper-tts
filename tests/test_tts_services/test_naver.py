from .base import TTSTests, logger
from hypertts_addon import languages


class TestNaver(TTSTests):

    def test_naver(self):
        # pytest tests/test_tts_services/ -k 'TestNaver and test_naver'
        service_name = 'Naver'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]
        assert len(service_voices) > 30

        self.random_voice_test(service_name, languages.AudioLanguage.ko_KR, '여보세요')
        self.random_voice_test(service_name, languages.AudioLanguage.ja_JP, 'おはようございます')


class TestNaverCLT(TestNaver):
    CONFIG_MODE = 'clt'
