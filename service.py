import sys
import abc
from posixpath import dirname
import typing

if hasattr(sys, '_pytest_mode'):
    import voice
    import services
    import services.voicelist
    import constants
else:
    # import running from within Anki
    from . import voice
    from . import services
    from .services import voicelist
    from . import constants

class ServiceBase(abc.ABC):
    
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
                            constants.AudioLanguage[v['language']], 
                            self, 
                            v['key'],
                            v['options']) for v in service_voices_json]
        return service_voices

    # the following functions can be overriden if a service requires configuration
    def configuration_options(self):
        return {}

    def configure(self):
        pass




