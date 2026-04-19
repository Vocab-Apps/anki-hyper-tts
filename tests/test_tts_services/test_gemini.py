import copy
import pytest

from .base import TTSTests, logger
from hypertts_addon import constants
from hypertts_addon import context
from hypertts_addon import errors
from hypertts_addon import languages
from hypertts_addon import voice as voice_module


class TestGemini(TTSTests):

    SERVICE_NAME = 'Gemini'

    def test_voice_list(self):
        voice_list = self.manager.full_voice_list()
        gemini_voices = [voice for voice in voice_list if voice.service == self.SERVICE_NAME]
        logger.info(f'found {len(gemini_voices)} voices for Gemini services')
        assert len(gemini_voices) >= 30

    def test_english(self):
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence')

    def test_french(self):
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.fr_FR
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'Je ne suis pas disponible.',
                                 voice_options={'language_code': 'fr-FR'})

    def test_japanese(self):
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.ja_JP
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'おはようございます',
                                 voice_options={'language_code': 'ja-JP'})

    @pytest.mark.skip(reason="ogg is actually supported on the CLT backend")
    def test_ogg_opus_unsupported(self):
        # ogg_opus format — not supported by Gemini service, should raise ServiceInputError
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        exception_caught = False
        try:
            self.manager.get_tts_audio('This is the first sentence', selected_voice,
                {'format': 'ogg_opus'},
                context.AudioRequestContext(constants.AudioRequestReason.batch))
        except errors.ServiceInputError as e:
            assert e.source_text == 'This is the first sentence'
            assert e.voice.service == self.SERVICE_NAME
            exception_caught = True
        assert exception_caught

    def test_model_gemini_3_1_flash_tts_preview(self):
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'model': 'gemini-3.1-flash-tts-preview'})

    def test_model_gemini_2_5_flash_tts(self):
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'model': 'gemini-2.5-flash-tts'})

    def test_model_gemini_2_5_pro_tts(self):
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'model': 'gemini-2.5-pro-tts'})

    def test_model_gemini_2_5_flash_lite_preview_tts(self):
        if self.CONFIG_MODE != 'clt':
            pytest.skip('gemini-2.5-flash-lite-preview-tts is not available on the Gemini API (direct mode)')
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'model': 'gemini-2.5-flash-lite-preview-tts'})

    def test_language_code_override(self):
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'Guten Morgen, wie geht es dir heute?',
                                 voice_options={'language_code': 'de-DE'})

    def test_prompt_style_control(self):
        # prompt (voice style control) — audio should still transcribe to the source text
        voice_list = self.manager.full_voice_list()
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'prompt': 'Speak in a cheerful, upbeat tone'})

    def test_invalid_voice_name(self):
        voice_list = self.manager.full_voice_list()
        selected_voice = self.pick_random_voice(voice_list, self.SERVICE_NAME, languages.AudioLanguage.en_US)
        selected_voice = copy.copy(selected_voice)
        voice_key = copy.copy(selected_voice.voice_key)
        voice_key['name'] = 'non existent'
        altered_voice = voice_module.TtsVoice_v3('non existent',
                                                 voice_key,
                                                 selected_voice.options,
                                                 self.SERVICE_NAME,
                                                 selected_voice.gender,
                                                 [languages.AudioLanguage.en_US],
                                                 constants.ServiceFee.paid)

        exception_caught = False
        try:
            self.manager.get_tts_audio('This is the second sentence', altered_voice, {},
                context.AudioRequestContext(constants.AudioRequestReason.batch))
        except (errors.RequestError, errors.ServiceRequestError) as e:
            assert e.source_text == 'This is the second sentence'
            assert e.voice.service == self.SERVICE_NAME
            exception_caught = True
        assert exception_caught


class TestGeminiCLT(TestGemini):
    CONFIG_MODE = 'clt'
