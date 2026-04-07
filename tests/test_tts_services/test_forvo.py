import unittest

from .base import TTSTests, logger
from hypertts_addon import constants
from hypertts_addon import errors
from hypertts_addon.languages import AudioLanguage


class TestForvo(TTSTests):

    def test_forvo(self):
        # pytest tests/test_tts_services/ -k 'TestForvo and test_forvo'
        service_name = 'Forvo'

        voice_list = self.manager.full_voice_list()
        service_voices = [voice for voice in voice_list if voice.service == service_name]
        assert len(service_voices) > 50

        # pick a random en_US voice
        self.random_voice_test(service_name, AudioLanguage.en_US, 'Camera')
        self.random_voice_test(service_name, AudioLanguage.fr_FR, 'ordinateur')

    def test_forvo_portuguese(self):
        # pytest tests/test_tts_services/ -k 'TestForvo and test_forvo_portuguese'
        service_name = 'Forvo'
        source_text = 'pomos'

        voice_list = self.manager.full_voice_list()

        # https://forvo.com/word/pomos/
        # as of 2025/01/04:
        # two recordings from brazil
        # no recordings from portugal

        # locate forvo portuguese-portugal voice
        # --------------------------------------
        candidates = [voice for voice in voice_list
                      if voice.service == service_name and
                      AudioLanguage.pt_PT in voice.audio_languages and
                      voice.gender == constants.Gender.Any]
        assert len(candidates) == 1
        forvo_portuguese_portugal_voice = candidates[0]

        # should return not found (AudioNotFoundError in direct mode, PermanentError in CLT mode)
        self.assertRaises(errors.PermanentError, self.verify_audio_output, forvo_portuguese_portugal_voice, AudioLanguage.pt_BR, source_text)


        # locate forvo portuguese-brazil voice
        # --------------------------------------
        candidates = [voice for voice in voice_list
                      if voice.service == service_name and
                      AudioLanguage.pt_BR in voice.audio_languages and
                      voice.gender == constants.Gender.Any]
        assert len(candidates) == 1
        forvo_portuguese_brazil_voice = candidates[0]

        # should return audio as we have recordings from brazil
        self.verify_audio_output(forvo_portuguese_brazil_voice, AudioLanguage.pt_PT, source_text)


class TestForvoCLT(TestForvo):
    CONFIG_MODE = 'clt'
