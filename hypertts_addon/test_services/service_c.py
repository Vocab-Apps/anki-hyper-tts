import sys
from hypertts_addon import constants
from hypertts_addon import service
from hypertts_addon import voice as voice_module

from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)

class ServiceC(service.ServiceBase):
    CONFIG_USER = 'user'
    CONFIG_PASSWORD = 'password'

    def __init__(self):
        self._config = {}
        self.user = None
        self.password = None

    def configure(self, config):
        self._config = config
        self.user = self.get_configuration_value_mandatory(self.CONFIG_USER)
        self.password = self.get_configuration_value_mandatory(self.CONFIG_PASSWORD)

    def test_service(self):
        return True

    def cloudlanguagetools_enabled(self):
        return True

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts        

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.paid

    def voice_list(self):
        # no voices, this service is just to test configuration
        return [
        ]

    def get_tts_audio(self, source_text, voice: voice_module.VoiceBase, options):
        raise Exception('not supported, dummy service')

    def configuration_options(self):
        return {
            self.CONFIG_USER: str,
            self.CONFIG_PASSWORD: str
        }