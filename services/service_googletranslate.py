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


lang = languages.AudioLanguage
LANGUAGE_KEY_MAP = {
    'fr': lang.fr_FR,
    'en': lang.en_US,
    'af': lang.af_ZA,
    'ar': lang.ar_XA,
    'bg': lang.bg_BG,
    'bn': lang.bn_BD,
    # 'bs': 
    'ca': lang.ca_ES,
    'cs': lang.cs_CZ,
    'cy': lang.cy_GB,
    'da': lang.da_DK,
    'de': lang.de_DE,
    'el': lang.el_GR,
    'eo': lang.eo_XX,
    'es': lang.es_ES,
    'et': lang.et_EE,
    'fi': lang.fi_FI,
    'gu': lang.gu_IN,
    'hi': lang.hi_IN,
    'hr': lang.hr_HR,
    'hu': lang.hu_HU,
    # 'hy': 
    'id': lang.id_ID,
    'is': lang.is_IS,
    'it': lang.it_IT,
    'ja': lang.ja_JP,
    'jw': lang.jv_ID,
    'km': lang.km_KH,
    'kn': lang.kn_IN,
    'ko': lang.ko_KR,
    # 'la': 
    'lv': lang.lv_LV,
    'mk': lang.mk_MK,
    'ml': lang.ml_IN,
    'mr': lang.mr_IN,
    'my': lang.my_MM,
    # 'ne':
    'nl': lang.nl_NL,
    # 'no': 
    'pl': lang.pl_PL,
    'pt': lang.pt_PT,
    'ro': lang.ro_RO,
    'ru': lang.ru_RU,
    'si': lang.si_LK,
    'sk': lang.sk_SK,
    # 'sq':
    'sr': lang.sr_RS,
    'su': lang.su_ID,
    'sv': lang.sv_SE,
    'sw': lang.sw_KE,
    'ta': lang.ta_IN,
    'te': lang.te_IN,
    'th': lang.th_TH,
    # 'tl': lang.
    'tr': lang.tr_TR,
    'uk': lang.uk_UA,
    'ur': lang.ur_PK,
    'vi': lang.vi_VN,
    'zh-CN': lang.zh_CN,
    'zh-TW': lang.zh_TW,
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
                voices.append(voice.Voice(language_key, constants.Gender.Female, language, self, language_key, {}))
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

