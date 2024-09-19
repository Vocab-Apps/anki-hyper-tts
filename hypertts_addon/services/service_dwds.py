import sys
import re
import requests
import bs4

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import logging_utils
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
        return constants.ServiceFee.free

    def build_voice(self, audio_language, voice_key):
        return voice.TtsVoice_v3(
            name=audio_language.lang.lang_name,
            gender=constants.Gender.Male,
            audio_languages=[audio_language],
            service=self.name,
            voice_key=voice_key,
            options={},
            service_fee=self.service_fee
        )

    def voice_list(self):
        return [
            voice.TtsVoice_v3(
                name='German',
                gender=constants.Gender.Female,
                audio_languages=[languages.AudioLanguage.de_DE],
                service=self.name,
                voice_key='german',
                options={},
                service_fee=self.service_fee
            )
        ]

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, options):

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
