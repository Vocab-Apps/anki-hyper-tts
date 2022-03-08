import sys
import requests
import json

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

class Watson(service.ServiceBase):
    CONFIG_SPEECH_KEY = 'speech_key'
    CONFIG_SPEECH_URL = 'speech_url'

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
            self.CONFIG_SPEECH_KEY: str,
            self.CONFIG_SPEECH_URL: str,
        }

    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        speech_key = self.get_configuration_value_mandatory(self.CONFIG_SPEECH_KEY)
        speech_url = self.get_configuration_value_mandatory(self.CONFIG_SPEECH_URL)

        base_url = speech_url
        url_path = '/v1/synthesize'
        voice_name = voice.voice_key["name"]
        constructed_url = base_url + url_path + f'?voice={voice_name}'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'audio/mp3'
        }

        data = {
            'text': source_text
        }

        response = requests.post(constructed_url, data=json.dumps(data), auth=('apikey', speech_key), headers=headers, timeout=constants.RequestTimeout)

        if response.status_code == 200:
            return response.content

        # otherwise, an error occured
        error_message = f"Status code: {response.status_code} reason: {response.reason}"
        raise errors.RequestError(source_text, voice, error_message)