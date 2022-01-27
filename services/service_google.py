import sys
import requests
import base64
import logging

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_services)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_services)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_services)

class Google(service.ServiceBase):
    CONFIG_API_KEY = 'api_key'

    def __init__(self):
        pass

    def cloudlanguagetools_enabled(self):
        return True

    def configure(self, config):
        self.config = config

    def configuration_options(self):
        return {
            self.CONFIG_API_KEY: str
        }

    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):

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

        logging.debug(f'requesting audio with payload {payload}')

        response = requests.post("https://texttospeech.googleapis.com/v1/text:synthesize?key={}".format(self.config[self.CONFIG_API_KEY]), json=payload)
        
        if response.status_code != 200:
            data = response.json()
            error_message = data.get('error', {}).get('message', str(data))
            logging.error(error_message)
            raise errors.RequestError(source_text, voice, error_message)

        data = response.json()
        encoded = data['audioContent']
        audio_content = base64.b64decode(encoded)

        return audio_content