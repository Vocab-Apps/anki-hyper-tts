import sys
import re
import requests
import bs4

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
languages = __import__('languages', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)

logger = logging_utils.get_child_logger(__name__)

class SpanishDict(service.ServiceBase):

    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.dictionary

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.free

    def build_voice(self, name, gender, audio_language, voice_key):
        return voice.TtsVoice_v3(
            name=name,
            gender=gender,
            audio_languages=[audio_language],
            service=self.name,
            voice_key=voice_key,
            options={},
            service_fee=self.service_fee
        )

    def voice_list(self):
        return [
            self.build_voice('Spanish', constants.Gender.Male, languages.AudioLanguage.es_ES, 'es'),
            self.build_voice('English', constants.Gender.Female, languages.AudioLanguage.en_US, 'en')
        ]

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, options):

        headers = {
		    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
        }

        language = voice.voice_key

        url = f'https://audio1.spanishdict.com/audio?lang={language}&text={source_text}'
        logger.debug(f'opening url {url}')
        response = requests.get(url, headers=headers)

        return response.content