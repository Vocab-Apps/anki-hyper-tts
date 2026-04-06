import pytest

from .base import TTSTests, logger
from hypertts_addon import languages
from hypertts_addon.languages import AudioLanguage


class TestOpenAI(TTSTests):

    def test_openai_english(self):
        # pytest tests/test_tts_services/ -k 'TestOpenAI and test_openai_english'
        service_name = 'OpenAI'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]
        assert len(service_voices) > 5

        # pick a random en_US voice
        self.random_voice_test(service_name, AudioLanguage.en_US, 'This is the first sentence')

        # test ogg format
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        self.verify_audio_output(selected_voice, AudioLanguage.en_US, 'This is the first sentence', voice_options={'format': 'ogg_opus'})

    @pytest.mark.skip(reason="openai for non-english languages doesn't produce reliable results")
    def test_openai_french(self):
        self.random_voice_test('OpenAI', languages.AudioLanguage.fr_FR, 'Il va pleuvoir demain.')


class TestOpenAICLT(TestOpenAI):
    CONFIG_MODE = 'clt'
