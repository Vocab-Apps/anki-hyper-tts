import sys
import requests


from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import options
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)

class OpenAI(service.ServiceBase):
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
        return constants.ServiceFee.paid

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

        url = 'https://api.openai.com/v1/audio/speech'

        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        # get voice options
        speed = voice_options.get('speed', voice.options['speed']['default'])
        model = voice_options.get('model', voice.options['model']['default'])
        instructions = voice_options.get('instructions', voice.options['instructions']['default'])
        audio_format_str = voice_options.get(options.AUDIO_FORMAT_PARAMETER, options.AudioFormat.mp3.name)
        audio_format = options.AudioFormat[audio_format_str]
        audio_format_map = {
            options.AudioFormat.mp3: 'mp3',
            options.AudioFormat.ogg_opus: 'opus'
        }
        response_format = audio_format_map[audio_format]

        data = {
            "model": model,
            "input": source_text,
            "voice": voice.voice_key['name'],
            'response_format': response_format,
            'speed': speed
        }
        
        # Only add instructions if they are not empty
        if instructions:
            data['instructions'] = instructions

        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        return response.content
