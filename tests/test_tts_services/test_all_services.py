from .base import TTSTests
from hypertts_addon import constants
from hypertts_addon import languages


class TestAllServices(TTSTests):

    def test_all_services_english(self):
        self.verify_all_services_language(constants.ServiceType.tts, languages.AudioLanguage.en_US, 'The weather is good today.')
        self.verify_all_services_language(constants.ServiceType.dictionary, languages.AudioLanguage.en_GB, 'camera')

    def test_all_services_french(self):
        self.verify_all_services_language(constants.ServiceType.tts, languages.AudioLanguage.fr_FR, 'Il va pleuvoir demain.')

    def test_all_services_mandarin(self):
        self.verify_all_services_language(constants.ServiceType.tts, languages.AudioLanguage.zh_CN, '赚钱', acceptable_solutions=['赚钱', '賺錢'])

    def test_all_services_japanese(self):
        self.verify_all_services_language(constants.ServiceType.tts, languages.AudioLanguage.ja_JP, 'おはようございます')


class TestAllServicesCLT(TestAllServices):
    CONFIG_MODE = 'clt'
