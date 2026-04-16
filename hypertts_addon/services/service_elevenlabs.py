import sys
import requests


from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import options
from hypertts_addon import logging_utils
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
        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)

        voice_id = voice.voice_key['voice_id']
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'

        # Handle audio format
        audio_format_str = voice_options.get(options.AUDIO_FORMAT_PARAMETER, voice.options.get(options.AUDIO_FORMAT_PARAMETER, {}).get('default', 'mp3'))
        if audio_format_str == 'ogg_opus':
            url += '?output_format=opus_48000_192'

        headers = {
            "Accept": "audio/mpeg",
            "xi-api-key": api_key
        }

        use_speaker_boost_str = voice_options.get('use_speaker_boost', voice.options.get('use_speaker_boost', {}).get('default', 'false'))

        data = {
            "text": source_text,
            "model_id": voice.voice_key['model_id'],
            "voice_settings": {
                "stability": voice_options.get('stability', voice.options['stability']['default']),
                "similarity_boost": voice_options.get('similarity_boost', voice.options['similarity_boost']['default']),
                "style": voice_options.get('style', voice.options.get('style', {}).get('default', 0.0)),
                "speed": voice_options.get('speed', voice.options.get('speed', {}).get('default', 1.0)),
                "use_speaker_boost": use_speaker_boost_str == 'true'
            }
        }

        # Add language_code if provided and not empty
        language_code = voice_options.get('language_code', voice.options.get('language_code', {}).get('default', ''))
        if language_code:
            data['language_code'] = language_code

        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 200:
            detail_message = None
            try:
                error_json = response.json()
                detail = error_json.get('detail', {})
                if isinstance(detail, dict):
                    detail_message = detail.get('message')
            except (ValueError, AttributeError):
                pass

            if response.status_code == 401:
                error_message = f'{self.name}: error processing TTS request: {response.status_code} {response.text}'
                logger.warning(error_message)
                raise errors.ServicePermissionError(source_text, voice, error_message)
            else:
                error_message = f'{self.name}: error processing TTS request: {response.status_code} {response.text}'
                logger.error(error_message)
                raise errors.RequestError(source_text, voice, error_message)

        return response.content
