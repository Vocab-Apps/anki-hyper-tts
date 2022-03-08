import sys
import requests
import base64

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

class CereProc(service.ServiceBase):
    CONFIG_USERNAME = 'username'
    CONFIG_PASSWORD = 'password'

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
            self.CONFIG_USERNAME: str,
            self.CONFIG_PASSWORD: str
        }

    def get_access_token(self):
        username = self.get_configuration_value_mandatory(self.CONFIG_USERNAME)
        password = self.get_configuration_value_mandatory(self.CONFIG_PASSWORD)
        combined = f'{username}:{password}'
        auth_string = base64.b64encode(combined.encode('utf-8')).decode('utf-8')
        headers = {'authorization': f'Basic {auth_string}'}

        auth_url = 'https://api.cerevoice.com/v2/auth'
        response = requests.get(auth_url, headers=headers, 
            timeout=constants.RequestTimeout)

        access_token = response.json()['access_token']        
        return access_token
    
    def get_auth_headers(self):
        headers={'Authorization': f'Bearer {self.get_access_token()}'}
        return headers

    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        voice_name = voice.voice_key['name']
        url = f'https://api.cerevoice.com/v2/speak?voice={voice_name}&audio_format=mp3'


        ssml_text = f"""<?xml version="1.0" encoding="UTF-8"?>
<speak xmlns="http://www.w3.org/2001/10/synthesis">{source_text}</speak>""".encode(encoding='utf-8')

        # logger.debug(f'querying url: {url}')
        response = requests.post(url, data=ssml_text, headers=self.get_auth_headers(), timeout=constants.RequestTimeout)

        if response.status_code == 200:
            return response.content

        # otherwise, an error occured
        error_message = f"status code: {response.status_code} reason: {response.reason}"
        raise errors.RequestError(source_text, voice, error_message)