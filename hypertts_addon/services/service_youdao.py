import sys
import requests

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import logging_utils

logger = logging_utils.get_child_logger(__name__)

class Youdao(service.ServiceBase):
    # https://youdao.com/result?word=vehicle&lang=en
    # Direct audio API: https://dict.youdao.com/dictvoice?audio=vehicle&type=2
    AUDIO_API_URL = 'https://dict.youdao.com/dictvoice'

    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.dictionary

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.free

    def build_voice(self, name, audio_language, voice_type):
        return voice.TtsVoice_v3(
            name=name,
            gender=constants.Gender.Male,
            audio_languages=[audio_language],
            service=self.name,
            voice_key={'type': voice_type},
            options={},
            service_fee=self.service_fee
        )

    def voice_list(self):
        return [
            self.build_voice('UK English', languages.AudioLanguage.en_GB, 1),
            self.build_voice('US English', languages.AudioLanguage.en_US, 2),
        ]

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, options):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
        }

        # Get the type parameter from voice options
        voice_type = voice.voice_key['type']
        # Build the API URL with parameters
        params = {
            'audio': source_text,
            'type': voice_type
        }
        
        logger.info(f'Requesting Youdao audio for "{source_text}" with type={voice_type}')
        
        try:
            response = requests.get(self.AUDIO_API_URL, params=params, headers=headers)
            
            # Check if we got a valid response
            if response.status_code == 200 and response.headers.get('Content-Type', '').startswith('audio/'):
                logger.info(f'Successfully retrieved audio for "{source_text}"')
                return response.content
            elif response.status_code == 500:
                # Youdao returns 500 for words that don't have pronunciations
                logger.warning(f'Word "{source_text}" not found in Youdao dictionary (HTTP 500)')
                raise errors.AudioNotFoundError(source_text, voice)
            else:
                logger.warning(f'Failed to get audio for "{source_text}": status={response.status_code}, content-type={response.headers.get("Content-Type", "unknown")}')
                raise errors.AudioNotFoundError(source_text, voice)
                
        except requests.exceptions.RequestException as e:
            logger.error(f'Request error for "{source_text}": {str(e)}')
            raise errors.AudioNotFoundError(source_text, voice)