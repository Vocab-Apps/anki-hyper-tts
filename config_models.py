import constants
import voice

"""
the various objects here dictate how HyperTTS is configured and these objects will serialize to/from the anki config
"""

class VoiceWithOptions():
    def __init__(self, voice: voice.VoiceBase, options):
        self.voice = voice
        self.options = options

    def serialize(self):
        return {
            'voice': self.voice.serialize(),
            'options': self.options
        }

    def options_str(self):
        options_array = []
        for key, value in self.options.items():
            if value != self.voice.options[key]['default']:
                options_array.append(f'{key}: {value}')
        if len(options_array) > 0:
            return ' (' + ', '.join(options_array) + ')'
        return ''


    def __str__(self):
        return f'{self.voice}{self.options_str()}'

class VoiceWithOptionsRandom(VoiceWithOptions):
    def __init__(self, voice: voice.VoiceBase, options):
        VoiceWithOptions.__init__(self, voice, options)

class VoiceWithOptionsPriority(VoiceWithOptions):
    def __init__(self, voice: voice.VoiceBase, options):
        VoiceWithOptions.__init__(self, voice, options)


class VoiceSelectionBase():
    def __init__(self):
        self._selection_mode = None

    def get_selection_mode(self):
        return self._selection_mode

    # properties
    selection_mode = property(get_selection_mode, None)

class VoiceSelectionSingle(VoiceSelectionBase):
    def __init__(self):
        VoiceSelectionBase.__init__(self)
        self._selection_mode = constants.VoiceSelectionMode.single
        self._voice_with_options = None
    
    def serialize(self):
        return {
            'voice_selection_mode': self._selection_mode.name,
            'voice': self._voice_with_options.serialize()
        }

    def get_voice(self):
        return self._voice_with_options
    def set_voice(self, voice_with_options):
        self._voice_with_options = voice_with_options

    voice = property(get_voice, set_voice)

class VoiceSelectionMultipleBase(VoiceSelectionBase):
    def __init__(self):
        VoiceSelectionBase.__init__(self)
        self._voice_list = []

    def get_voice_list(self):
        return self._voice_list

    def clear_voice_list(self):
        self._voice_list = []

    def add_voice(self):
        pass

    voice_list = property(get_voice_list, None)


class VoiceSelectionRandom(VoiceSelectionMultipleBase):
    def __init__(self):
        VoiceSelectionBase.__init__(self)
        self._selection_mode = constants.VoiceSelectionMode.random

class VoiceSelectionPriority(VoiceSelectionMultipleBase):
    def __init__(self):
        VoiceSelectionBase.__init__(self)
        self._selection_mode = constants.VoiceSelectionMode.priority

