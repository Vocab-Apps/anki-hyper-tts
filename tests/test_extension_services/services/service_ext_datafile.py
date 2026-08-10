"""fixture third party service which loads a data file sitting next to it, resolved through
__file__. service_openrouter.py in the anki-hyper-tts-extensions repository does exactly this, so the
extension loading mechanism has to set __file__ correctly."""

import json
import os

from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import service
from hypertts_addon import voice as voice_module

_HERE = os.path.dirname(os.path.abspath(__file__))
_VOICES_JSON = os.path.join(_HERE, 'ext_datafile_voices.json')


class ExtensionServiceDataFile(service.ServiceBase):
    def __init__(self):
        service.ServiceBase.__init__(self)
        with open(_VOICES_JSON, 'r', encoding='utf-8') as f:
            self.voice_names = json.load(f)['voices']

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.free

    def voice_list(self):
        return [
            voice_module.build_voice_v3(voice_name, constants.Gender.Female,
                languages.AudioLanguage.en_US, self, {'name': voice_name}, {})
            for voice_name in self.voice_names
        ]

    def get_tts_audio(self, source_text, voice: voice_module.TtsVoice_v3, options):
        return source_text.encode('utf-8')
