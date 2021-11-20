import constants
import service
import voice
import services.voicelist
import json

class Google(service.ServiceBase):
    def __init__(self):
        pass

    def voice_list(self):
        google_voices_json = [voice for voice in services.voicelist.VOICE_LIST if voice['service'] == self.name]
        google_voices = [voice.Voice(v['name'], constants.Gender[v['gender']], constants.AudioLanguage[v['language']], self, v['key']) for v in google_voices_json]
        return google_voices

    def get_tts_audio(self, source_text, voice: voice.VoiceBase):
        self.requested_audio = {
            'source_text': source_text,
            'voice_key': voice.voice_key,
            'language': voice.language.name
        }
        encoded_dict = json.dumps(self.requested_audio, indent=2).encode('utf-8')
        return encoded_dict    