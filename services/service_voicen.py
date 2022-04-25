import sys
import requests
import time


voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

class Voicen(service.ServiceBase):
    CONFIG_API_KEY = 'api_key'

    def __init__(self):
        service.ServiceBase.__init__(self)

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

    def get_headers(self, api_key):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {api_key}'
        }
        return headers

    def job_status_ready(self, api_key, job_id, source_text, voice):
        check_status_url = f'https://tts.voicen.com/api/v1/jobs/{job_id}/'
        response = requests.get(check_status_url, headers=self.get_headers(api_key), timeout=constants.RequestTimeout)
        status = response.json()['data']['status']        
        if status == 'ready':
            return True
        if status == 'failed':
            error_message = f"Job {job_id} status failed"
            raise errors.RequestError(source_text, voice, error_message)
        return False


    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)

        # create the audio request
        # ========================
        request_url = 'https://tts.voicen.com/api/v1/jobs/text/'
        data = {
            'text': source_text,
            'lang': voice.voice_key['lang'],
            'voice_id': voice.voice_key['voice_id']
        }

        logger.info(f'requesting audio for {source_text}')
        response = requests.post(request_url, json=data, headers=self.get_headers(api_key), timeout=constants.RequestTimeout)
        if response.status_code != 200:
            error_message = f"Status code: {response.status_code} reason: {response.reason}"
            raise errors.RequestError(source_text, voice, error_message)


        response_data = response.json()
        job_id = response_data['data']['id']

        # wait for job to be ready
        # ========================
        total_tries = 7
        max_tries = total_tries
        wait_time = 0.2        
        job_ready = False
        while job_ready == False and max_tries > 0:
            time.sleep(wait_time)            
            logger.debug(f'checking whether job_id {job_id} is ready')
            job_ready = self.job_status_ready(api_key, job_id, source_text, voice)
            wait_time = wait_time * 2
            max_tries -= 1             

        # retrieve audio
        # ==============

        retrieve_url = f'https://tts.voicen.com/api/v1/jobs/{job_id}/synthesize/'
        logger.info(f'retrieving result from url {retrieve_url}')
        response = requests.get(retrieve_url, headers=self.get_headers(api_key))

        if response.status_code == 200:
            return response.content

        # otherwise, an error occured
        error_message = f"Status code: {response.status_code} reason: {response.reason}"
        raise errors.RequestError(source_text, voice, error_message)