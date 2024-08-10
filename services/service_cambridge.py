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

class Cambridge(service.ServiceBase):
    # https://dictionary.cambridge.org/dictionary/english/vehicle
    WEBSITE = 'https://dictionary.cambridge.org'
    SEARCH_URL = WEBSITE + '/dictionary/english/'

    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.dictionary

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.free

    def build_voice(self, name, audio_language, voice_key):
        return voice.TtsVoice_v3(
            name=name,
            gender=constants.Gender.Female,
            audio_languages=[audio_language],
            service=self.name,
            voice_key=voice_key,
            options={},
            service_fee=self.service_fee
        )

    def voice_list(self):
        return [
            self.build_voice('UK', languages.AudioLanguage.en_GB, 'uk'),
            self.build_voice('US', languages.AudioLanguage.en_US, 'us')
        ]

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, options):
        headers = {
		    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
        }

        complete_url = self.SEARCH_URL + source_text
        logger.info(f'loading url: {complete_url}')
        response = requests.get(complete_url, headers=headers)

        soup = bs4.BeautifulSoup(response.content, 'html.parser')

        section_class_map = {
            languages.AudioLanguage.en_GB: 'uk dpron-i',
            languages.AudioLanguage.en_US: 'us dpron-i',
        }
        wanted_class = section_class_map[voice.audio_languages[0]]
        logger.debug(f'wanted_class: [{wanted_class}]')
        
        # <span class="uk dpron-i ">
        span_pronunciation_section = soup.find('span', {'class': wanted_class})
        logger.debug(f'span_pronunciation_section: {span_pronunciation_section}')
        if span_pronunciation_section != None:
            source_tag = span_pronunciation_section.find('source', {'type': 'audio/mpeg'})
            if source_tag != None:
                sound_url = self.WEBSITE + source_tag['src']
                response = requests.get(sound_url, headers=headers)
                return response.content                

        # if we couldn't locate the source tag, raise notfound
        raise errors.AudioNotFoundError(source_text, voice)