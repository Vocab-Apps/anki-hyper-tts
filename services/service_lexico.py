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

class Lexico(service.ServiceBase):

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
        ]

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        headers = {
		    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0',
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
			'Accept-Language': 'en-US,en;q=0.5'
        }
        url = f'https://www.lexico.com/search?filter=en_dictionary&dictionary=en&s=t&query={source_text}'
        logger.debug(f'loading url: {url}')
        response = requests.get(url, headers=headers)
        logger.debug(f'response.status_code: {response.status_code}')
         
        if response.status_code != 200:
            logger.debug(response.content)
        
        soup = bs4.BeautifulSoup(response.content, 'html.parser')

        h3_pronunciations = soup.find('h3', {'class': 'pronunciations'})
        if h3_pronunciations != None:
            audio_tag = h3_pronunciations.find('audio')
            if audio_tag != None:
                sound_url = audio_tag['src']
                response = requests.get(sound_url, headers=headers)
                return response.content                            

        # if we couldn't locate the source tag, raise notfound
        raise errors.AudioNotFoundError(source_text, voice)
