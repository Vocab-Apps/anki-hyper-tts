import constants
import service
import voice
import typing
import json


class ServiceA(service.ServiceBase):
    def __init__(self):
        pass

    def voice_list(self):
        return [
            voice.Voice('voice_a_1', constants.Gender.male, constants.Language.fr, self, {'name': 'voice_1'}),
            voice.Voice('voice_a_2', constants.Gender.female, constants.Language.en, self, {'name': 'voice_2'})
        ]

    def get_tts_audio(self, source_text, voice: voice.VoiceBase):
        self.requested_audio = {
            'source_text': source_text,
            'voice_key': voice.voice_key,
            'language': voice.language.name
        }
        encoded_dict = json.dumps(self.requested_audio, indent=2).encode('utf-8')
        return encoded_dict    