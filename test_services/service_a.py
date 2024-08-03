import sys
import constants
import languages
import service
import voice
import typing
import json
import time


options = __import__('options', globals(), locals(), [], sys._addon_import_level_services)
voice_module = __import__('voice', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_services)
logger = logging_utils.get_child_logger(__name__)

VOICE_OPTIONS = {
    'pitch': {
        'default': 0.0, 'max': 20.0, 'min': -20.0, 'type': 'number'}, 
    'speaking_rate': {
        'default': 1.0, 'max': 4.0, 'min': 0.25, 'type': 'number'},
    'style': {
        'default': 1, 'max': 3, 'min': 0, 'type': 'number_int'},
    options.AUDIO_FORMAT_PARAMETER: {
        'type': options.ParameterType.list.name,
        'values': [
            options.AudioFormat.ogg_opus.name,
            options.AudioFormat.mp3.name,
        ],
        'default': options.AudioFormat.mp3.name
    }

}

class ServiceA(service.ServiceBase):
    def __init__(self):
        self._config = {}

    def configure(self, config):
        self._config = config
        api_key = self.get_configuration_value_mandatory('api_key')

    def test_service(self):
        return True

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts        

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.free

    def voice_list(self):
        return [
            voice.build_voice_v3('voice_a_1', constants.Gender.Male, languages.AudioLanguage.fr_FR, self, {'name': 'voice_1'}, VOICE_OPTIONS),
            voice.build_voice_v3('voice_a_2', constants.Gender.Female, languages.AudioLanguage.en_US, self, {'name': 'voice_2'}, VOICE_OPTIONS),
            voice.build_voice_v3('voice_a_3', constants.Gender.Female, languages.AudioLanguage.ja_JP, self, {'name': 'voice_3'}, VOICE_OPTIONS),
        ]

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, options):
        delay_s = self._config.get('delay', 0)
        if delay_s > 0:
            logger.info(f'sleeping for {delay_s}s')
            time.sleep(delay_s)

        self.requested_audio = {
            'source_text': source_text,
            'voice': voice_module.serialize_voice_v3(voice),
            'options': options
        }
        encoded_dict = json.dumps(self.requested_audio, indent=2).encode('utf-8')
        return encoded_dict    

    def configuration_options(self):
        return {
            'api_key': str,
            'region': ['us', 'europe'],
            'delay': int,
            'demo_key': bool
        }