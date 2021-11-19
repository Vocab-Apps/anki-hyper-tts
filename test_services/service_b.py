import service
import voice

class ServiceB(service.ServiceBase):
    def __init__(self):
        pass

    def voice_list(self):
        return []

    def get_tts_audio(self, source_text, voice: voice.VoiceBase):
        raise Exception('not implemented')        