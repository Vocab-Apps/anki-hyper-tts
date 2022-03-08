import sys
import requests
import time


voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

class FptAi(service.ServiceBase):
    CONFIG_API_KEY = 'api_key'

    def __init__(self):
        service.ServiceBase.__init__(self)
        self.access_token = None

    def cloudlanguagetools_enabled(self):
        return True

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.Premium

    def configuration_options(self):
        return {
            self.CONFIG_API_KEY: str,
        }

    def voice_list(self):
        return self.basic_voice_list()

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