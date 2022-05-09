import enum

AUDIO_FORMAT_PARAMETER = 'format'

class ParameterType(enum.Enum):
    number = enum.auto() # floating point number
    number_int = enum.auto() # integer number
    list = enum.auto() # list of possible string values

class AudioFormat(enum.Enum):
    mp3 = enum.auto()
    ogg_opus = enum.auto()
    ogg_vorbis = enum.auto()