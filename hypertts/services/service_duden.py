import sys
import re
import requests
import bs4

from hypertts import voice
from hypertts import service
from hypertts import errors
from hypertts import constants
from hypertts import languages
from hypertts import logging_utils
logger = logging_utils.get_child_logger(__name__)

class Duden(service.ServiceBase):
    # https://www.duden.de/rechtschreibung/Gesundheit
    WEBSITE_HOME = 'https://www.duden.de'
    SEARCH_URL = WEBSITE_HOME + '/rechtschreibung/'

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
            self.build_voice(languages.AudioLanguage.de_DE, 'german')
        ]

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, options):
        headers = {
		    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
        }

        full_url = self.SEARCH_URL + source_text
        response = requests.get(full_url, headers=headers)

        soup = bs4.BeautifulSoup(response.content, 'html.parser')

        sound_a_tag = soup.find('a', {'class': 'pronunciation-guide__sound'})

        if sound_a_tag != None:
            sound_url = sound_a_tag['href']
            logger.info(f'downloading url {sound_url}')
            response = requests.get(sound_url, headers=headers)
            return response.content
        else:
            logger.warning(f'could not find audio for {source_text} (source tag not found)')        
        
        # if we couldn't locate the source tag, raise notfound
        raise errors.AudioNotFoundError(source_text, voice)
