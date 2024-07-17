import sys
import requests
import datetime
import time
import urllib
import json


voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
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
        return constants.ServiceFee.Premium

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
        language = f"/language/{voice.voice_key['language_code']}"
        limit = f'/limit/1'
        order = f'/order/rate-desc'

        sex_param = ''
        if 'gender' in voice.voice_key:
            sex_param = f"/sex/{voice.voice_key['gender']}"
        
        country_param = ''
        if voice.voice_key['country_code'] != self.COUNTRY_ANY:
            # user selected a particular country
            country_param = f"/country/{voice.voice_key['country_code']}"

        # parse the comma separated list of prefered usernames to get the audio
        exclude_param = options.get('exclude_others', voice.options['exclude_others']['default'])
        preferred_usernames = options.get('preferred_users', voice.options['preferred_users']['default']).split(',')
        if len(preferred_usernames) > 0:
            # Using Forvo API to filter by username will result into multiple API calls which are expensive.
            # Instead, increase the result limit and do the username matching ourselves.
            limit = f'/limit/10'

        encoded_text = urllib.parse.quote(source_text)
        url = f'{api_url}/key/{api_key}/format/json/action/word-pronunciations/word/{encoded_text}{language}{order}{limit}{country_param}{sex_param}'
        response = requests.get(url, headers=headers, timeout=constants.RequestTimeout)
        if response.status_code != 200:
            error_message = f'status_code: {response.status_code} response: {response.content}'
            logger.debug(f'Forvo: Unable to handle request {error_message}')

            if response.status_code == 400:
                # handle daily API calls limit error as a Audio not found to allow other voices to kick-in    
                raise errors.AudioNotFoundError(source_text, voice)

            # unknown error, signal the request error            
            raise errors.RequestError(source_text, voice, error_message)

        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error(f'Forvo: could not decode JSON for url {url}: {response.content}')
            raise errors.RequestError(source_text, voice, 'Could not retrieve audio from Forvo')
        
        results = []
        items = data['items']
        if len(items) == 0:
            raise errors.AudioNotFoundError(source_text, voice)

        if len(preferred_usernames) > 0:
            # match the usernames in the same order they were defined in the voice options.
            for username in preferred_usernames:
                results = [i for i in items if i['username'] == username]
                if len(results) > 0:
                    logger.debug(f'Forvo: Found audio for {source_text} by prefered user {username}')
                    break
        
        if len(results) == 0:
            # exclude results from other usernames (non-preferred)
            if exclude_param == 'yes':
                logger.debug(f'Forvo: No preferred username was found for {source_text}')
                raise errors.AudioNotFoundError(source_text, voice)
            
            # fallback to the fist result when either of the following occurs:
            #   1) no prefered usernames were provided (and others were not excluded)
            #   2) none of the results matched a preferred username.
            results = items

        audio_url = results[0]['pathmp3']
        username = results[0]['username']
        logger.debug(f'Forvo: Obtaining audio for {source_text} by username {username}')
        audio_request = requests.get(audio_url, headers=headers, timeout=constants.RequestTimeout)
        return audio_request.content