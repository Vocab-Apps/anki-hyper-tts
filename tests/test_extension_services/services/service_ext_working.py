"""fixture third party service, stands in for a well behaved service from the
anki-hyper-tts-extensions repository. note that it imports hypertts_addon the same way the real
extension services do."""

import json

from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import service
from hypertts_addon import voice as voice_module


class ExtensionServiceWorking(service.ServiceBase):
    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.free

    def voice_list(self):
        return [
            voice_module.build_voice_v3('extension_voice_1', constants.Gender.Male,
                languages.AudioLanguage.fr_FR, self, {'name': 'extension_voice_1'}, {}),
        ]

    def get_tts_audio(self, source_text, voice: voice_module.TtsVoice_v3, options):
        return json.dumps({'source_text': source_text}).encode('utf-8')

    def configuration_options(self):
        return {
            'api_key': str,
        }
