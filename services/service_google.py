import constants
import service
import voice
import services.voicelist
import json
import requests
import base64

class Google(service.ServiceBase):
    def __init__(self):
        pass

    def voice_list(self):
        google_voices_json = [voice for voice in services.voicelist.VOICE_LIST if voice['service'] == self.name]
        google_voices = [voice.Voice(v['name'], 
                                     constants.Gender[v['gender']], 
                                     constants.AudioLanguage[v['language']], 
                                     self, 
                                     v['key'],
                                     v['options']) for v in google_voices_json]
        return google_voices

    def get_tts_audio(self, source_text, voice: voice.VoiceBase):

        payload = {
            "audioConfig": {
                "audioEncoding": "MP3",
                "pitch": voice['options']['pitch']['default'],
                "speakingRate": voice['options']['speed']['default'],
            },
            "input": {
                "ssml": f"<speak>{source_text}</speak>"
            },
            "voice": {
                "languageCode": voice.get_voice_key()['language_code'],
                "name": voice.get_voice_key()['name'],
            }
        }

        r = requests.post("https://texttospeech.googleapis.com/v1/text:synthesize?key={}".format(options['key']), headers=headers, json=payload)
        r.raise_for_status()

        data = r.json()
        encoded = data['audioContent']
        audio_content = base64.b64decode(encoded)

        return audio_content