import sys
import abc
import dataclasses
import databind.json
from typing import Dict, Any, List

constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
languages = __import__('languages', globals(), locals(), [], sys._addon_import_level_base)

class VoiceBase(abc.ABC):
    """
    abstract base class which defines all the mandatory properties
    """

    @abc.abstractproperty
    def name():
        pass
    
    @abc.abstractproperty
    def gender() -> constants.Gender:
        pass

    @abc.abstractproperty
    def language() -> languages.AudioLanguage:
        pass

    @abc.abstractproperty
    def service():
        pass

    @abc.abstractproperty
    def voice_key():
        pass

    @abc.abstractproperty
    def options():
        pass

    def serialize(self):
        return {
            'name': self.name,
            'gender': self.gender.name,
            'language': self.language.name,
            'service': self.service.name,
            'voice_key': self.voice_key
        }

    def __str__(self):
        return f'{self.language.audio_lang_name}, {self.gender.name}, {self.name}, {self.service.name}'

    def __eq__(self, other):
        return self.service.name == other.service.name and self.voice_key == other.voice_key


class Voice(VoiceBase):
    """
    this basic implementation can be used by services which don't have a particular requirement
    """

    def __init__(self, name, gender, language, service, voice_key, options):
        self._name = name
        self._gender = gender
        self._language = language
        self._service = service
        self._voice_key = voice_key
        self._options = options

    def _get_name(self):
        return self._name

    def _get_gender(self):
        return self._gender

    def _get_language(self):
        return self._language

    def _get_service(self):
        return self._service
    
    def _get_voice_key(self):
        return self._voice_key

    def _get_options(self):
        return self._options

    def __repr__(self):
        return f'{self.service} {self.name}, {self.language}'

    name = property(fget=_get_name)
    gender = property(fget=_get_gender)
    language = property(fget=_get_language)
    service = property(fget=_get_service)
    voice_key = property(fget=_get_voice_key)
    options = property(fget=_get_options)

# these classes are used with API version 3
# support for multilingual voices

# voice identification only
@dataclasses.dataclass
class TtsVoiceId_v3:
    voice_key: Dict[str, Any]
    service: str

    def __eq__(self, other):
        if not isinstance(other, TtsVoiceId_v3):
            return NotImplemented
        return self.voice_key == other.voice_key and self.service == other.service

    def __hash__(self):
        return hash((self.voice_key['voice_id'], self.service))

# full voice information (to display in the GUI)
@dataclasses.dataclass
class TtsVoice_v3:
    name: str
    voice_key: Dict[str, Any]
    options: Dict[str, Dict[str, Any]]
    service: str
    gender: constants.Gender
    audio_languages: List[languages.AudioLanguage]
    service_fee: constants.ServiceFee

    @property
    def voice_id(self) -> TtsVoiceId_v3:
        return self.get_voice_id()

    def get_voice_id(self) -> TtsVoiceId_v3:
        return TtsVoiceId_v3(voice_key=self.voice_key, service=self.service)

    def serialize_voice_id(self):
        return serialize_voiceid_v3(self.get_voice_id())

    def __str__(self):
        return f"{self.name}, {self.gender.name}, {self.service}"

    def __repr__(self):
            return (f"TtsVoice_v3(name={self.name!r}, voice_key={self.voice_key!r}, options={self.options!r}, "
                    f"service={self.service!r}, gender={self.gender!r}, audio_languages={self.audio_languages!r}, "
                    f"service_fee={self.service_fee!r}, voice_id={self.voice_id!r})")

def serialize_voice_v3(voice: TtsVoice_v3) -> str:
    return databind.json.dump(voice, TtsVoice_v3)

def deserialize_voice_v3(voice: str) -> TtsVoice_v3:
    return databind.json.load(voice, TtsVoice_v3)

def serialize_voiceid_v3(voice_id: TtsVoiceId_v3) -> str:
    return databind.json.dump(voice_id, TtsVoiceId_v3)

def deserialize_voice_id_v3(voice_id: str) -> TtsVoiceId_v3:
    return databind.json.load(voice_id, TtsVoiceId_v3)

def build_voice_v3(name, gender, language, service, voice_key, options) -> TtsVoice_v3:
    return TtsVoice_v3(
        name=name,
        voice_key=voice_key,
        options=options,
        service=service.name,
        gender=gender,
        audio_languages=[language],
        service_fee=service.service_fee
    )