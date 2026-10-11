from .base import TTSTests
from hypertts_addon import languages


class TestAlibaba(TTSTests):

    def test_alibaba_chinese(self):
        # the two syllables of '赚钱' get misheard for a couple of voices (Xiaoyue, Xiaomei), this
        # longer sentence is recognized for all 33 voices. whisper often transcribes in traditional
        # characters
        self.random_voice_test('Alibaba', languages.AudioLanguage.zh_CN, '今天天气很好',
                               acceptable_solutions=['今天天气很好', '今天天氣很好'])


class TestAlibabaCLT(TestAlibaba):
    CONFIG_MODE = 'clt'
