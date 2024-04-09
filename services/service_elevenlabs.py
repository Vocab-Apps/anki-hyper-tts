import sys
import requests


voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_services)
options = __import__('options', globals(), locals(), [], sys._addon_import_level_services)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

class ElevenLabs(service.ServiceBase):
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
            self.CONFIG_API_KEY: str
        }

    def configure(self, config):
        self._config = config
        self.api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)

    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, voice_options):
        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)

        voice_id = voice.voice_key['voice_id']
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'

        headers = {
            "Accept": "application/json",
            "xi-api-key": api_key
        }
        headers['Accept'] = "audio/mpeg"

        data = {
            "text": source_text,
            "model_id": voice.voice_key['model_id'],
            "voice_settings": {
                "stability": voice_options.get('stability', voice.options['stability']['default']),
                "similarity_boost": voice_options.get('similarity_boost', voice.options['similarity_boost']['default'])
            }
        }

        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 200:
            error_message = f'{self.name}: error processing TTS request: {response.status_code} {response.text}'
            if response.status_code in [401]:
                # API key issue, or quota exceeded
                logger.warning(error_message)
            else:
                logger.error(error_message)
            raise errors.RequestError(source_text, voice, error_message)

        response.raise_for_status()
        
        return response.content
