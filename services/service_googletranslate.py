import sys
import time
import gtts
import io


voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
languages = __import__('languages', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)


lang = languages.AudioLanguage
LANGUAGE_KEY_MAP = {
    'id': lang.id_ID,
    'is': lang.is_IS,
    'iw': lang.he_IL,
    'pt': lang.pt_PT,
    'sr': lang.sr_RS,
    'zh-CN': lang.zh_CN,
    'zh': lang.zh_CN,
    'zh-TW': lang.zh_TW,
}

GENDER_MAP = {
    'ko': constants.Gender.Male
}

class GoogleTranslate(service.ServiceBase):
    CONFIG_THROTTLE_SECONDS = 'throttle_seconds'

    def __init__(self):
        service.ServiceBase.__init__(self)

    def configuration_options(self):
        return {
            self.CONFIG_THROTTLE_SECONDS: float
        }

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.Free

    def get_language(self, language_key):
        # check if we have this language in AudioLanguageDefaults
        if language_key in languages.Language.__members__:
            language = languages.Language[language_key]
            if language in languages.AudioLanguageDefaults:
                return languages.AudioLanguageDefaults[language]
        # do we have an override for this language
        if language_key in LANGUAGE_KEY_MAP:
            return LANGUAGE_KEY_MAP[language_key]
        return None

    def voice_list(self):
        languages = gtts.lang.tts_langs()
        # pprint.pprint(languages)
        voices = []
        for language_key, language_name in languages.items():
            language = self.get_language(language_key)
            if language == None:
                logger.error(f'{self.name}: could not process language {language_key}')
            else:
                gender = GENDER_MAP.get(language_key, constants.Gender.Female)
                voices.append(voice.Voice(language_key, gender, language, self, language_key, {}))
        return voices

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        # configuration options
        throttle_seconds = self.get_configuration_value_optional(self.CONFIG_THROTTLE_SECONDS, 0)

        if throttle_seconds > 0:
            time.sleep(throttle_seconds)

        try:
            tts = gtts.gTTS(text=source_text, lang=voice.voice_key)
            buffer = io.BytesIO()
            tts.write_to_fp(buffer)

            return buffer.getbuffer()
        except gtts.gTTSError as e:
            logger.warning(f'exception while retrieving sound for {source_text}: {e}')
            # this error will be handled, and not reported as unusual
            raise errors.RequestError(source_text, voice, str(e))


