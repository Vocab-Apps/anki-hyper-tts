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

    def configure(self, config):
        self.config = config

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
                "pitch": voice.options['pitch']['default'],
                "speakingRate": voice.options['speaking_rate']['default'],
            },
            "input": {
                "ssml": f"<speak>{source_text}</speak>"
            },
            "voice": {
                "languageCode": voice.voice_key['language_code'],
                "name": voice.voice_key['name'],
            }
        }

        response = requests.post("https://texttospeech.googleapis.com/v1/text:synthesize?key={}".format(self.config['api_key']), json=payload)

        data = response.json()
        encoded = data['audioContent']
        audio_content = base64.b64decode(encoded)

        return audio_content