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

        # Network failures (requests.exceptions.Timeout / ConnectionError) are
        # deliberately not caught here: ServiceManager._get_tts_audio_service
        # maps them to the retryable ServiceTimeoutError / ServiceConnectionError.
        # They used to be swallowed into the permanent AudioNotFoundError
        # (Sentry ANKI-HYPER-TTS-M28: a ReadTimeout on dict.youdao.com was
        # reported as "Audio not found" and never retried).
        response = requests.get(self.AUDIO_API_URL, params=params, headers=headers, timeout=constants.RequestTimeout)

        content_type = response.headers.get('Content-Type', '')
        if response.status_code == 200:
            if content_type.startswith('audio/'):
                logger.info(f'Successfully retrieved audio for "{source_text}"')
                return response.content
            # 200 with a non-audio body: Youdao has no pronunciation for this text
            logger.warning(f'Word "{source_text}" not found in Youdao dictionary (content-type={content_type or "unknown"})')
            raise errors.AudioNotFoundError(source_text, voice)
        if response.status_code in (404, 500):
            # Youdao returns 500 for words that don't have pronunciations
            logger.warning(f'Word "{source_text}" not found in Youdao dictionary (HTTP {response.status_code})')
            raise errors.AudioNotFoundError(source_text, voice)

        error_message = f'got status_code {response.status_code} from {self.AUDIO_API_URL}, content-type={content_type or "unknown"}'
        logger.warning(f'Failed to get audio for "{source_text}": {error_message}')
        if response.status_code == 429:
            raise errors.RateLimitRetryAfterError(source_text, voice, error_message,
                                                  _retry_after_seconds(response))
        if response.status_code in (502, 503, 504):
            raise errors.ServiceGatewayError(source_text, voice, error_message)
        raise errors.UnknownServiceError(source_text, voice, error_message)


def _retry_after_seconds(response, default=60):
    retry_after = response.headers.get('Retry-After')
    if retry_after is None:
        return default
    try:
        return max(1, int(float(retry_after)))
    except (TypeError, ValueError):
        return default
