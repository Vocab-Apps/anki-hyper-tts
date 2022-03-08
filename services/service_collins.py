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

class Collins(service.ServiceBase):
    COLLINS_WEBSITE = 'https://www.collinsdictionary.com'
    SEARCH_URL = COLLINS_WEBSITE + '/search/'

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
            self.build_voice(languages.AudioLanguage.en_GB, 'english'),
            self.build_voice(languages.AudioLanguage.fr_FR, 'french-english'),
            self.build_voice(languages.AudioLanguage.de_DE, 'german-english'),
            self.build_voice(languages.AudioLanguage.es_ES, 'spanish-english'),
            self.build_voice(languages.AudioLanguage.it_IT, 'italian-english'),
        ]

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        headers = {
		    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
        }
        search_params = {
            'dictCode': voice.voice_key,
            'q': source_text
        }
        response = requests.get(self.SEARCH_URL, params=search_params, headers=headers)
        
        # word not found ?
        if '/spellcheck/' in response.url:
            raise errors.AudioNotFoundError(source_text, voice)
        if response.status_code != 200:
            raise errors.RequestError(source_text, voice, f'search returned status code {response.status_code}')
        
        soup = bs4.BeautifulSoup(response.content, 'html.parser')
        headword_div = soup.find('div', {'class': 'he'})
        sound_tag = headword_div.find('a', {
            "class":'hwd_sound', 
        })
        if sound_tag == None:
            raise errors.AudioNotFoundError(source_text, voice)
        sound_url = sound_tag['data-src-mp3']
        logger.info(f'found sound_url: {sound_url}')

        logger.info(f'downloading url {sound_url}')
        response = requests.get(sound_url, headers=headers)
        if response.status_code != 200:
            raise errors.RequestError(source_text, voice, f'download audio returned status code {response.status_code} ({sound_url})')

        return response.content