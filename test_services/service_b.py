import constants
import service
import voice

class VoiceB(voice.VoiceBase):

    def __init__(self, voice_id, service):
        self._voice_id = voice_id
        self._service = service

    def _get_name(self):
        return self._voice_id

    def _get_gender(self):
        return constants.Gender.Male

    def _get_language(self):
        return constants.AudioLanguage.ja_JP

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

    def voice_list(self):
        return [
            VoiceB('alex', self),
            VoiceB('jane', self)
        ]

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        raise Exception('not implemented')        