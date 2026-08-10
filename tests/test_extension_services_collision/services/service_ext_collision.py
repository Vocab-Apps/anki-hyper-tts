"""fixture third party service whose class name collides with an existing service. built-in
services must win, otherwise an extension could silently shadow a built-in service and inherit its
stored configuration (service_enabled / service_config are keyed by class name)."""

from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import service
from hypertts_addon import voice as voice_module


class ServiceA(service.ServiceBase):
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
            voice_module.build_voice_v3('collision_voice', constants.Gender.Male,
                languages.AudioLanguage.fr_FR, self, {'name': 'collision_voice'}, {}),
        ]

    def get_tts_audio(self, source_text, voice: voice_module.TtsVoice_v3, options):
        return source_text.encode('utf-8')
