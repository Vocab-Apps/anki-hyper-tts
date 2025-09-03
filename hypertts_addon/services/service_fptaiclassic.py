import sys
import requests
import time


from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import logging_utils
from hypertts_addon import languages
logger = logging_utils.get_child_logger(__name__)

FPTAI_VOICE_SPEED_DEFAULT = 0

class FptAiClassic(service.ServiceBase):
    CONFIG_API_KEY = 'api_key'

    def __init__(self):
        service.ServiceBase.__init__(self)
        self.access_token = None

    def cloudlanguagetools_enabled(self):
        return False

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.paid

    def configuration_options(self):
        return {
            self.CONFIG_API_KEY: str,
        }

    def build_voice(self, voice_id: str, name: str, gender, region: str):
        return voice.TtsVoice_v3(
            name=f'{name} ({region})',
            gender=gender,
            audio_languages=[languages.AudioLanguage.vi_VN],
            service=self.name,
            voice_key={
                'voice_id': voice_id,
            },
            options={
                'speed': {
                    'type': 'number',
                    'min': -3,
                    'max': 3,
                    'default': FPTAI_VOICE_SPEED_DEFAULT
                },
            },
            service_fee=self.service_fee
        )

    def voice_list(self):
        return [
            self.build_voice('leminh', 'Lê Minh', constants.Gender.Male, 'miền Bắc'),
            self.build_voice('banmai', 'Ban Mai', constants.Gender.Female, 'miền Bắc'),
            self.build_voice('thuminh', 'Thu Minh', constants.Gender.Female, 'miền Bắc'),
            self.build_voice('giahuy', 'Gia Huy', constants.Gender.Male, 'miền Trung'),
            self.build_voice('ngoclam', 'Ngọc Lam', constants.Gender.Female, 'miền Trung'),
            self.build_voice('myan', 'Mỹ An', constants.Gender.Female, 'miền Trung'),
            self.build_voice('lannhi', 'Lan Nhi', constants.Gender.Female, 'miền Nam'),
            self.build_voice('linhsan', 'Linh San', constants.Gender.Female, 'miền Nam'),
            self.build_voice('minhquang', 'Minh Quang', constants.Gender.Male, 'miền Nam'),
            # acesound voices
            self.build_voice('banmaiace', 'Ban Mai (AceSound)', constants.Gender.Female, 'miền Bắc'),
            self.build_voice('thuminhace', 'Thu Minh (AceSound)', constants.Gender.Female, 'miền Bắc'),
            self.build_voice('ngoclamace', 'Ngọc Lam (AceSound)', constants.Gender.Female, 'miền Trung'),
            self.build_voice('linhsanace', 'Linh San (AceSound)', constants.Gender.Female, 'miền Nam'),
            self.build_voice('minhquangace', 'Minh Quang (AceSound)', constants.Gender.Male, 'miền Nam'),
       ]

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)

        api_url = "https://api.fpt.ai/hmi/tts/v5"
        body = source_text
        headers = {
            'api_key': api_key,
            'voice': voice.voice_key['voice_id'],
            'Cache-Control': 'no-cache',
            'format': 'mp3',
        }
        if 'speed' in options:
            headers['speed'] = str(options.get('speed'))
        response = requests.post(api_url, headers=headers, data=body.encode('utf-8'), 
            timeout=constants.RequestTimeout)

        if response.status_code == 200:
            response_data = response.json()
            async_url = response_data['async']
            logger.debug(f'received async_url: {async_url}')

            # wait until the audio is available
            audio_available = False
            total_tries = 7
            max_tries = total_tries
            wait_time = 0.2
            while max_tries > 0:
                time.sleep(wait_time)
                logger.debug(f'checking whether audio is available on {async_url}')
                response = requests.get(async_url, allow_redirects=True, timeout=constants.RequestTimeout)
                if response.status_code == 200 and len(response.content) > 0:
                    return response.content
                wait_time = wait_time * 2
                max_tries -= 1            
            
            error_message = f'could not retrieve audio after {total_tries} tries (url {async_url})'
            raise errors.RequestError(source_text, voice, error_message)

        error_message = f'could not retrieve FPT.AI audio: {response.content}'
        raise errors.RequestError(source_text, voice, error_message)