import sys
import requests
import base64
import logging
import time
import gtts
import tempfile
import pprint

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
languages = __import__('languages', globals(), locals(), [], sys._addon_import_level_services)


AudioLanguage = languages.AudioLanguage
LANGUAGE_KEY_MAP = {
    'fr': AudioLanguage.fr_FR,
    'en': AudioLanguage.en_US,
}


class GoogleTranslate(service.ServiceBase):
    CONFIG_THROTTLE_SECONDS = 'throttle_seconds'

    def __init__(self):
        service.ServiceBase.__init__(self)

    def configuration_options(self):
        return {
            self.CONFIG_THROTTLE_SECONDS: float
        }

    def voice_list(self):
        languages = gtts.lang.tts_langs()
        # pprint.pprint(languages)
        voices = []
        for language_key, language_name in languages.items():
            if language_key in LANGUAGE_KEY_MAP:
                language = LANGUAGE_KEY_MAP[language_key]
                voices.append(voice.Voice(language_key, constants.Gender.Male, language, self, language_key, {}))
            else:
                logging.warning(f'skipping voice {language_key}, no mapping found')
        return voices

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        # configuration options
        throttle_seconds = self.get_configuration_value_optional(self.CONFIG_THROTTLE_SECONDS, 0)

        if throttle_seconds > 0:
            time.sleep(throttle_seconds)

        # create temporary file
        audio_tempfile = tempfile.NamedTemporaryFile(suffix='.mp3', prefix='hypertts_google_translate_')
        tts = gtts.gTTS(text=source_text, lang=voice.voice_key)
        tts.save(audio_tempfile.name)

        logging.info(f'wrote audio to {audio_tempfile.name}')

        # read tempfile content
        f = open(audio_tempfile.name, mode='rb')
        audio_content = f.read()

        return audio_content

