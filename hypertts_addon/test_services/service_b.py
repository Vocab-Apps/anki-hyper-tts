import sys
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import service
from hypertts_addon import voice
from hypertts_addon import errors

from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)

class VoiceB(voice.VoiceBase):

    def __init__(self, voice_id, service):
        self._voice_id = voice_id
        self._service = service

    def _get_name(self):
        return self._voice_id

    def _get_gender(self):
        return constants.Gender.Male

    def _get_language(self):
        return languages.AudioLanguage.ja_JP

    def _get_service(self):
        return self._service
    
    def _get_voice_key(self):
        return {'voice_id': self._voice_id}

    def _get_options(self):
        return {}

    name = property(fget=_get_name)
    gender = property(fget=_get_gender)
    language = property(fget=_get_language)
    service = property(fget=_get_service)
    voice_key = property(fget=_get_voice_key)
    options = property(fget=_get_options)

class ServiceB(service.ServiceBase):
    def __init__(self):
        pass

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

    def build_voice(self, voice_name):
        return voice.build_voice_v3(voice_name, constants.Gender.Male, languages.AudioLanguage.ja_JP, self, {'voice_id': voice_name}, {})

    def voice_list(self):
        return [
            self.build_voice('alex'),
            self.build_voice('jane'),
            self.build_voice('notfound')
        ]

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        if voice.voice_key['voice_id'] == 'notfound':
            logger.warning('special notfound voice')
            raise errors.AudioNotFoundError(source_text, voice)
        raise Exception('not implemented')

    def configuration_options(self):
        return {
            'user_key': str
        }        