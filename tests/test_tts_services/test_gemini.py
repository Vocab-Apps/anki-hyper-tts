import copy

from .base import TTSTests, logger
from hypertts_addon import constants
from hypertts_addon import context
from hypertts_addon import errors
from hypertts_addon import languages
from hypertts_addon import voice as voice_module


class TestGemini(TTSTests):

    def test_gemini(self):
        service_name = 'Gemini'

        voice_list = self.manager.full_voice_list()
        gemini_voices = [voice for voice in voice_list if voice.service == 'Gemini']
        logger.info(f'found {len(gemini_voices)} voices for Gemini services')
        assert len(gemini_voices) >= 30

        # english
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, service_name, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence')

        # french (explicit language_code)
        audio_language = languages.AudioLanguage.fr_FR
        selected_voice = self.pick_random_voice(voice_list, service_name, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'Je ne suis pas disponible.',
                                 voice_options={'language_code': 'fr-FR'})

        # japanese (non-Latin script, explicit language_code)
        audio_language = languages.AudioLanguage.ja_JP
        selected_voice = self.pick_random_voice(voice_list, service_name, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'おはようございます',
                                 voice_options={'language_code': 'ja-JP'})

        # ogg_opus format — not supported by Gemini service, should raise ServiceInputError
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, service_name, audio_language)
        exception_caught = False
        try:
            self.manager.get_tts_audio('This is the first sentence', selected_voice,
                {'format': 'ogg_opus'},
                context.AudioRequestContext(constants.AudioRequestReason.batch))
        except errors.ServiceInputError as e:
            assert e.source_text == 'This is the first sentence'
            assert e.voice.service == 'Gemini'
            exception_caught = True
        assert exception_caught

        # non-default model
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, service_name, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'model': 'gemini-2.5-flash-preview-tts'})

        # prompt (voice style control) — audio should still transcribe to the source text
        audio_language = languages.AudioLanguage.en_US
        selected_voice = self.pick_random_voice(voice_list, service_name, audio_language)
        self.verify_audio_output(selected_voice, audio_language, 'This is the first sentence',
                                 voice_options={'prompt': 'Speak in a cheerful, upbeat tone'})

        # error checking — invalid voice name
        selected_voice = self.pick_random_voice(voice_list, service_name, languages.AudioLanguage.en_US)
        selected_voice = copy.copy(selected_voice)
        voice_key = copy.copy(selected_voice.voice_key)
        voice_key['name'] = 'non existent'
        altered_voice = voice_module.TtsVoice_v3('non existent',
                                                 voice_key,
                                                 selected_voice.options,
                                                 service_name,
                                                 selected_voice.gender,
                                                 [languages.AudioLanguage.en_US],
                                                 constants.ServiceFee.paid)

        exception_caught = False
        try:
            self.manager.get_tts_audio('This is the second sentence', altered_voice, {},
                context.AudioRequestContext(constants.AudioRequestReason.batch))
        except (errors.RequestError, errors.ServiceRequestError) as e:
            assert e.source_text == 'This is the second sentence'
            assert e.voice.service == 'Gemini'
            exception_caught = True
        assert exception_caught


class TestGeminiCLT(TestGemini):
    CONFIG_MODE = 'clt'
