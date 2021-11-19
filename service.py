import abc
import typing
import voice

class ServiceBase():

    @abc.abstractmethod
    def voice_list(self) -> typing.List[voice.VoiceBase]:
        pass