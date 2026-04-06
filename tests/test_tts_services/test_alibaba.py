from .base import TTSTests
from hypertts_addon import languages


class TestAlibaba(TTSTests):

    def test_alibaba_chinese(self):
        self.random_voice_test('Alibaba', languages.AudioLanguage.zh_CN, '赚钱')


class TestAlibabaCLT(TestAlibaba):
    CONFIG_MODE = 'clt'
