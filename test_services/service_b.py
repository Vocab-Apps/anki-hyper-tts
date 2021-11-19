import constants
import service
import voice

class VoiceB(voice.VoiceBase):

    def __init__(self, voice_id):
        self._voice_id = voice_id

    def _get_name(self):
        return self._voice_id

    def _get_gender(self):
        return constants.Gender.male

    def _get_language(self):
        return constants.Language.ja

    def _get_service(self):
        return 'ServiceB'
    
    def _get_voice_key(self):
        return {'voice_id': self._voice_id}

    name = property(fget=_get_name)
    gender = property(fget=_get_gender)
    language = property(fget=_get_language)
    service = property(fget=_get_service)
    voice_key = property(fget=_get_voice_key)    

class ServiceB(service.ServiceBase):
    def __init__(self):
        pass

    def voice_list(self):
        return [
            VoiceB('alex'),
            VoiceB('jane')
        ]

    def get_tts_audio(self, source_text, voice: voice.VoiceBase):
        raise Exception('not implemented')        