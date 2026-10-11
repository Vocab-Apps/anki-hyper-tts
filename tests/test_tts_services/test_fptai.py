from .base import TTSTests
from hypertts_addon import languages


class TestFptAi(TTSTests):

    def test_fptai(self):
        # pytest tests/test_tts_services/ -k 'TestFptAi and test_fptai'
        # 'Tôi bị mất cái ví.' was misheard by whisper for 5 of the 9 FptAi voices;
        # this sentence is transcribed correctly for all of them
        self.random_voice_test('FptAi', languages.AudioLanguage.vi_VN, 'Hôm nay trời đẹp quá.')


class TestFptAiCLT(TestFptAi):
    CONFIG_MODE = 'clt'
