import sys
import requests
import json

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

class Naver(service.ServiceBase):
    CONFIG_CLIENT_ID = 'client_id'
    CONFIG_CLIENT_SECRET = 'client_secret'

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
            self.CONFIG_CLIENT_ID: str,
            self.CONFIG_CLIENT_SECRET: str,
        }

    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        client_id = self.get_configuration_value_mandatory(self.CONFIG_CLIENT_ID)
        client_secret = self.get_configuration_value_mandatory(self.CONFIG_CLIENT_SECRET)

        url = 'https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-NCP-APIGW-API-KEY-ID': client_id,
            'X-NCP-APIGW-API-KEY': client_secret
        }

        data = {
            'text': source_text,
            'speaker': voice.voice_key['name'],
            'speed': options.get('speed', voice.options['speed']['default']),
            'pitch': options.get('pitch', voice.options['pitch']['default'])
        }

        # alternate_data = 'speaker=clara&text=vehicle&volume=0&speed=0&pitch=0&format=mp3'
        response = requests.post(url, data=data, headers=headers, timeout=constants.RequestTimeout)
        if response.status_code == 200:
            return response.content

        response_data = response.json()
        error_message = f'Status code: {response.status_code}: {response_data}'
        raise errors.RequestError(source_text, voice, error_message)
