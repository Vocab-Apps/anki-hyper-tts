import sys
import re
import requests
import bs4
import urllib.parse

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import logging_utils
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

        # Replace German umlauts with their traditional representations for Duden URLs
        # Duden uses ae, oe, ue instead of ä, ö, ü in their URLs
        url_text = source_text
        url_text = url_text.replace('ä', 'ae')
        url_text = url_text.replace('ö', 'oe')
        url_text = url_text.replace('ü', 'ue')
        url_text = url_text.replace('Ä', 'Ae')
        url_text = url_text.replace('Ö', 'Oe')
        url_text = url_text.replace('Ü', 'Ue')
        # Note: ß replacement to 'ss' doesn't seem to work consistently on Duden
        
        # URL encode the text after replacements
        encoded_text = urllib.parse.quote(url_text)
        full_url = self.SEARCH_URL + encoded_text
        logger.info(f'Requesting Duden URL: {full_url} (original text: {source_text})')
        response = requests.get(full_url, headers=headers)

        soup = bs4.BeautifulSoup(response.content, 'html.parser')

        pronunciation_button = soup.find('button', {'class': 'pronunciation-guide__sound'})

        if pronunciation_button is not None:
            sound_url = pronunciation_button['data-href']
            logger.info(f'downloading url {sound_url}')
            response = requests.get(sound_url, headers=headers)
            return response.content
        else:
            logger.warning(f'could not find audio for {source_text} (source tag not found)')

        # if we couldn't locate the source tag, raise notfound
        raise errors.AudioNotFoundError(source_text, voice)
