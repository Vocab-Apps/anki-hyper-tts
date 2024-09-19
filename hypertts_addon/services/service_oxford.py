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

class Oxford(service.ServiceBase):
    URL_BASE = 'https://www.oxfordlearnersdictionaries.com/definition/english/'

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
            self.build_voice(languages.AudioLanguage.en_GB, languages.AudioLanguage.en_GB.name),
            self.build_voice(languages.AudioLanguage.en_US, languages.AudioLanguage.en_US.name),
        ]

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, options):
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
        wanted_class = section_class_map[voice.audio_languages[0]]
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
