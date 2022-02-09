import sys
import abc
from posixpath import dirname
import typing

if hasattr(sys, '_pytest_mode'):
    import services.voicelist
else:
    # import running from within Anki
    from .services import voicelist

constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_base)
services = __import__('services', globals(), locals(), [], sys._addon_import_level_base)
languages = __import__('languages', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)

class ServiceBase(abc.ABC):
    def __init__(self):
        self._config = {}
    
    """service name"""
    def _get_name(self):
        return type(self).__name__

    name = property(fget=_get_name)

    # enable/disable the service
    def _get_enabled(self):
        if not hasattr(self, '_enabled'):
            return self.enabled_by_default()
        if self._enabled == None:
            return False
        return self._enabled
    
    def _set_enabled(self, enabled):
        self._enabled = enabled

    enabled = property(fget=_get_enabled, fset=_set_enabled)

    # whether the service is supported by cloud-language-tools
    def cloudlanguagetools_enabled(self):
        return False # default

    # whether the service is enabled by default
    def enabled_by_default(self):
        return False

    @property
    @abc.abstractmethod
    def service_type(self) -> constants.ServiceType:
        pass

    @property
    @abc.abstractmethod
    def service_fee(self) -> constants.ServiceFee:
        pass    

    def test_service(self):
        return False

    @abc.abstractmethod
    def voice_list(self) -> typing.List[voice.VoiceBase]:
        pass

    @abc.abstractmethod
    def get_tts_audio(self, source_text, voice: voice.VoiceBase, options):
        pass

    # some helper functions
    def basic_voice_list(self) -> typing.List[voice.VoiceBase]:
        """basic processing for voice list which should work for most services which are represented in voicelist.py"""
        service_voices_json = [voice for voice in services.voicelist.VOICE_LIST if voice['service'] == self.name]
        service_voices = [voice.Voice(v['name'], 
                            constants.Gender[v['gender']], 
                            languages.AudioLanguage[v['language']], 
                            self, 
                            v['key'],
                            v['options']) for v in service_voices_json]
        return service_voices

    # the following functions can be overriden if a service requires configuration
    def configuration_options(self):
        return {}

    def configure(self, config):
        self._config = config

    def get_configuration_value_mandatory(self, key):
        value = self._config.get(key, None)
        if value == None or (self.configuration_options()[key] == str and len(value) == 0):
            raise errors.MissingServiceConfiguration(self.name, key)
        return value

    def get_configuration_value_optional(self, key, default_value):
        return self._config.get(key, default_value)

