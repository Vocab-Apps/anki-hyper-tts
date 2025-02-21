import sys
import requests
import datetime
import time
import urllib
import json


from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)

class Forvo(service.ServiceBase):
    CONFIG_API_KEY = 'api_key'
    CONFIG_API_URL = 'api_url'
    CONFIG_THROTTLE_SECONDS = 'throttle_seconds'

    CONFIG_API_URL_FREE = 'https://apifree.forvo.com/'
    CONFIG_API_URL_COMMERCIAL = 'https://apicommercial.forvo.com/'
    CONFIG_API_URL_CORPORATE = 'https://apicorporate.forvo.com/api2/v1.1/'

    COUNTRY_ANY = 'ANY'

    def __init__(self):
        service.ServiceBase.__init__(self)
        self.access_token = None

    def cloudlanguagetools_enabled(self):
        return True

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.dictionary

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.paid

    def configuration_options(self):
        return {
            self.CONFIG_API_KEY: str,
            self.CONFIG_API_URL: [
                self.CONFIG_API_URL_FREE,
                self.CONFIG_API_URL_COMMERCIAL,
                self.CONFIG_API_URL_CORPORATE,
            ],
            self.CONFIG_THROTTLE_SECONDS: float
        }


    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):

        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)
        api_url = self.get_configuration_value_optional(self.CONFIG_API_URL, self.CONFIG_API_URL_FREE)
        throttle_seconds = self.get_configuration_value_optional(self.CONFIG_THROTTLE_SECONDS, 0)

        if throttle_seconds > 0:
            time.sleep(throttle_seconds)

        # prevent getting blocked by cloudflare
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0'}

        language = voice.voice_key['language_code']

        sex_param = ''
        if 'gender' in voice.voice_key:
            sex_param = f"/sex/{voice.voice_key['gender']}"
        
        country_code = ''
        if voice.voice_key['country_code'] != self.COUNTRY_ANY:
            # user selected a particular country
            country_code = f"/country/{voice.voice_key['country_code']}"

        username_param = ''
        # skip this for now, add it back in later        
        # if 'preferred_user' in voice_key:
        #     username_param = f"/username/{voice_key['preferred_user']}"

        encoded_text = urllib.parse.quote(source_text)
        corporate_url = api_url == self.CONFIG_API_URL_CORPORATE

        if corporate_url:
            url = f'{api_url}{api_key}/word-pronunciations/word/{encoded_text}/language/{language}{sex_param}/order/rate-desc/limit/1{country_code}'
        else:
            url = f'{api_url}/key/{api_key}/format/json/action/word-pronunciations/word/{encoded_text}/language/{language}{sex_param}{username_param}/order/rate-desc/limit/1{country_code}'

        response = requests.get(url, headers=headers, timeout=constants.RequestTimeout)
        if response.status_code == 200:
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.error(f'Forvo: could not decode JSON for url {url}: {response.content}')
                raise errors.RequestError(source_text, voice, 'Could not retrieve audio from Forvo')
            if corporate_url:
                items = data['data']['items']
            else:
                items = data['items']
            if len(items) == 0:
                raise errors.AudioNotFoundError(source_text, voice)
            audio_url = items[0]['pathmp3']
            audio_request = requests.get(audio_url, headers=headers, timeout=constants.RequestTimeout)
            return audio_request.content

        error_message = f'status_code: {response.status_code} response: {response.content}'
        raise errors.RequestError(source_text, voice, error_message)
