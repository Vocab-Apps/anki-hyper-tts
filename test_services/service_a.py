import constants
import service
import voice
import typing


class ServiceA(service.ServiceBase):
    def __init__(self):
        pass

    def voice_list(self):
        return [
            voice.Voice('voice_a_1', constants.Gender.male, constants.Language.fr, 'ServiceA', {'name': 'voice_1'}),
            voice.Voice('voice_a_2', constants.Gender.female, constants.Language.en, 'ServiceA', {'name': 'voice_2'})
        ]
