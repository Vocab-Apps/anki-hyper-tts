import requests
import time
from typing import List

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)



class NaverPapago(service.ServiceBase):
    CONFIG_THROTTLE_SECONDS = 'throttle_seconds'

    # The site was rewritten to Next.js and the TTS endpoints moved from
    # /apis/tts/* to /api/tts/* (2025). The old HMAC-based PPG authorization
    # scheme was dropped with the rewrite; the endpoints now require no auth.
    TTS_ENDPOINT = 'https://papago.naver.com/api/tts/'
    MAKE_ID_ENDPOINT = TTS_ENDPOINT + 'makeID'

    def __init__(self):
        service.ServiceBase.__init__(self)

    def configuration_options(self):
        return {
            self.CONFIG_THROTTLE_SECONDS: float
        }

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.free

    def build_voice(self, audio_language, gender, speaker_name):
        return voice.TtsVoice_v3(
            name=speaker_name,
            gender=gender,
            audio_languages=[audio_language],
            service=self.name,
            voice_key=speaker_name,
            options={},
            service_fee=self.service_fee
        )

    def voice_list(self) -> List[voice.TtsVoice_v3]:
        return [
            self.build_voice(languages.AudioLanguage.ko_KR, constants.Gender.Female, 'kyuri'),
            self.build_voice(languages.AudioLanguage.ja_JP, constants.Gender.Female, 'yuri'),
            self.build_voice(languages.AudioLanguage.en_US, constants.Gender.Female, 'clara'),
            self.build_voice(languages.AudioLanguage.zh_CN, constants.Gender.Female, 'meimei'),
            self.build_voice(languages.AudioLanguage.zh_TW, constants.Gender.Female, 'chiahua'),
            self.build_voice(languages.AudioLanguage.es_ES, constants.Gender.Female, 'carmen'),
            self.build_voice(languages.AudioLanguage.fr_FR, constants.Gender.Female, 'roxane'),
            self.build_voice(languages.AudioLanguage.de_DE, constants.Gender.Female, 'lena'),
            self.build_voice(languages.AudioLanguage.ru_RU, constants.Gender.Female, 'vera'),
            self.build_voice(languages.AudioLanguage.th_TH, constants.Gender.Female, 'somsi'),
        ]

    def generate_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://papago.naver.com',
            'Referer': 'https://papago.naver.com/',
        }

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, options):
        # configuration options
        throttle_seconds = self.get_configuration_value_optional(self.CONFIG_THROTTLE_SECONDS, 0)
        if throttle_seconds > 0:
            time.sleep(throttle_seconds)

        url = self.MAKE_ID_ENDPOINT
        params = {
            'alpha': 0,
            'pitch': 0,
            'speaker': voice.voice_key,
            'speed': 0,
            'text': source_text,
        }
        headers = self.generate_headers()
        logger.info(f'executing POST request on {url} with headers={headers}, data={params}')
        response = requests.post(url, headers=headers, data=params, timeout=constants.RequestTimeout)
        if response.status_code != 200:
            self._raise_for_status(source_text, voice, response, url)

        response_data = response.json()
        sound_id = response_data['id']
        logger.info(f'retrieved sound_id successfully: {sound_id}')

        # actually retrieve sound file
        # ============================

        final_url = self.TTS_ENDPOINT + sound_id
        logger.info(f'final_url: {final_url}')

        response = requests.get(final_url, headers=headers, timeout=constants.RequestTimeout)
        if response.status_code != 200:
            self._raise_for_status(source_text, voice, response, final_url)
        return response.content

    def _raise_for_status(self, source_text, voice, response, url):
        """Map a non-200 Papago response to the right ServiceRequestError subclass.

        These used to be raised as the legacy, non-retry-aware RequestError
        (Sentry ANKI-HYPER-TTS-HHB: HTTP 400 {"errorCode":"-10001",
        "errorMessage":"INVALID_REQUEST"}, e.g. Korean text on the Chinese
        'meimei' speaker), which left the retry logic without a disposition.
        """
        error_message = f'got status_code {response.status_code} from {url}: {response.content}'
        logger.warning(error_message)
        status_code = response.status_code
        if status_code == 400:
            # the text / speaker combination is rejected: retrying won't help
            raise errors.ServiceInputError(source_text, voice, error_message)
        if status_code in (401, 403):
            raise errors.ServicePermissionError(source_text, voice, error_message)
        if status_code == 429:
            retry_after = response.headers.get('Retry-After')
            retry_after_seconds = 60
            if retry_after is not None:
                try:
                    retry_after_seconds = max(1, int(float(retry_after)))
                except (TypeError, ValueError):
                    pass
            raise errors.RateLimitRetryAfterError(source_text, voice, error_message, retry_after_seconds)
        if status_code in (502, 503, 504):
            raise errors.ServiceGatewayError(source_text, voice, error_message)
        raise errors.UnknownServiceError(source_text, voice, error_message)
