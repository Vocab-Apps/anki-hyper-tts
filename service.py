import abc
import typing
import voice
import services
import constants

class ServiceBase(abc.ABC):

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

    @abc.abstractmethod
    def voice_list(self) -> typing.List[voice.VoiceBase]:
        pass

    @abc.abstractmethod
    def get_tts_audio(self, source_text, voice: voice.VoiceBase):
        pass

    """service name"""
    def _get_name(self):
        return type(self).__name__

    name = property(fget=_get_name)
