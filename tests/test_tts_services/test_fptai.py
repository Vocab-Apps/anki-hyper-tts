from .base import TTSTests
from hypertts_addon import languages


class TestFptAi(TTSTests):

    def test_fptai(self):
        # pytest tests/test_tts_services/ -k 'TestFptAi and test_fptai'
        self.random_voice_test('FptAi', languages.AudioLanguage.vi_VN, 'Tôi bị mất cái ví.',
                               acceptable_solutions=['Tôi bị mất cái ví.',
                                                      'cứ bị mất cái ví',
                                                      'cơ bị mất kế ví',
                                                      'có bị mất cái ví'])


class TestFptAiCLT(TestFptAi):
    CONFIG_MODE = 'clt'
