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

class Oxford(service.ServiceBase):
    URL_BASE = 'https://www.oxfordlearnersdictionaries.com/definition/english/'

    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.dictionary

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.Free

    def build_voice(self, audio_language, voice_key):
        return voice.Voice(audio_language.lang.lang_name, constants.Gender.Male, audio_language, self, voice_key, {})

    def voice_list(self):
        return [
            self.build_voice(languages.AudioLanguage.en_GB, languages.AudioLanguage.en_GB.name),
            self.build_voice(languages.AudioLanguage.en_US, languages.AudioLanguage.en_US.name),
        ]

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        headers = {
		    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
        }
        url = self.URL_BASE + source_text
        logger.debug(f'loading url: {url}')
        response = requests.get(url, headers=headers)
        logger.debug(f'response.status_code: {response.status_code}')
        
        soup = bs4.BeautifulSoup(response.content, 'html.parser')

        section_class_map = {
            languages.AudioLanguage.en_GB: 'pron-uk',
            languages.AudioLanguage.en_US: 'pron-us',
        }
        wanted_class = section_class_map[voice.language]
        logger.debug(f'wanted_class: [{wanted_class}]')

        # <span class="uk dpron-i ">
        div_pronunciation = soup.find('div', {'class': f'sound audio_play_button {wanted_class} icon-audio'})
        # logger.debug(f'span_pronunciation_section: {span_pronunciation_section}')
        if div_pronunciation != None:
            sound_url = div_pronunciation['data-src-mp3']
            if sound_url != None:
                response = requests.get(sound_url, headers=headers)
                return response.content                

        # if we couldn't locate the source tag, raise notfound
        raise errors.AudioNotFoundError(source_text, voice)
