import abc
import constants

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
    def language() -> constants.AudioLanguage:
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

class VoiceWithOptions():
    def __init__(self, voice: VoiceBase, options):
        self.voice = voice
        self.options = options

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

    def __str__(self):
        return f'{self._service.name}: {self.name}'

    name = property(fget=_get_name)
    gender = property(fget=_get_gender)
    language = property(fget=_get_language)
    service = property(fget=_get_service)
    voice_key = property(fget=_get_voice_key)
    options = property(fget=_get_options)
