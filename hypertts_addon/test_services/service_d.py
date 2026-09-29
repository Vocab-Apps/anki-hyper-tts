from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import options
from hypertts_addon import service
from hypertts_addon import voice as voice_module
import json

from hypertts_addon import logging_utils

logger = logging_utils.get_child_logger(__name__)

# a service with multilingual voices, like Gemini (Kore can be told a language)
# and OpenAI (alloy cannot)

KORE_OPTIONS = {
    'model': {
        'type': options.ParameterType.list.name,
        'values': ['model-fast', 'model-hd'],
        'default': 'model-fast'
    },
    'language_code': {
        'type': options.ParameterType.text.name,
        'default': 'en-US'
    },
    'prompt': {
        'type': options.ParameterType.text.name,
        'default': ''
    },
}

ALLOY_OPTIONS = {
    'speed': {
        'default': 1.0, 'max': 4.0, 'min': 0.25, 'type': 'number'},
}

class ServiceD(service.ServiceBase):
    def __init__(self):
        self._config = {}

    def configure(self, config):
        self._config = config

    def test_service(self):
        return True

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.paid

    def voice_list(self):
        return [
            voice_module.TtsVoice_v3(
                name='Kore (Firm)',
                voice_key={'name': 'Kore'},
                options=KORE_OPTIONS,
                service=self.name,
                gender=constants.Gender.Female,
                audio_languages=[languages.AudioLanguage.es_ES, languages.AudioLanguage.es_MX, languages.AudioLanguage.fr_FR],
                service_fee=self.service_fee),
            voice_module.TtsVoice_v3(
                name='alloy',
                voice_key={'name': 'alloy'},
                options=ALLOY_OPTIONS,
                service=self.name,
                gender=constants.Gender.Female,
                audio_languages=[languages.AudioLanguage.es_ES, languages.AudioLanguage.es_MX, languages.AudioLanguage.en_US],
                service_fee=self.service_fee),
        ]

    def can_send_audio_language(self, voice: voice_module.TtsVoice_v3) -> bool:
        return voice.voice_key['name'] == 'Kore'

    def get_tts_audio(self, source_text, voice: voice_module.TtsVoice_v3, options):
        chosen_audio_language = voice_module.get_chosen_audio_language(voice)
        self.requested_audio = {
            'source_text': source_text,
            'voice_key': voice.voice_key,
            'chosen_audio_language': chosen_audio_language.name if chosen_audio_language else None,
            'options': options
        }
        return json.dumps(self.requested_audio, indent=2).encode('utf-8')
