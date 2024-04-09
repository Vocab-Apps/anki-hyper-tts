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

class DigitalesWorterbuchDeutschenSprache(service.ServiceBase):
    WEBSITE_HOME = 'https://www.dwds.de'
    SEARCH_URL = WEBSITE_HOME + '/wb/'

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
            voice.Voice('German', constants.Gender.Female, languages.AudioLanguage.de_DE, self, 'german', {})
        ]

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):

        headers = {
		    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
        }

        full_url = self.SEARCH_URL + source_text
        response = requests.get(full_url, headers=headers)

        soup = bs4.BeautifulSoup(response.content, 'html.parser')

        source_tag = soup.find('source', {'type': 'audio/mpeg'})

        if source_tag != None:
            sound_url = source_tag['src']
            logger.info(f'downloading url {sound_url}')
            response = requests.get(sound_url, headers=headers)
            return response.content
        else:
            logger.warning(f'could not find audio for {source_text} (source tag not found)')
        
        # if we couldn't locate the source tag, raise notfound
        raise errors.AudioNotFoundError(source_text, voice)
