import abc
import typing
import voice

class ServiceBase(abc.ABC):

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