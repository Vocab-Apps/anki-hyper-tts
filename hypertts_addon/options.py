import enum

AUDIO_FORMAT_PARAMETER = 'format'

class ParameterType(enum.Enum):
    number = enum.auto() # floating point number
    number_int = enum.auto() # integer number
    list = enum.auto() # list of possible string values
    text = enum.auto() # text input field

class AudioFormat(enum.Enum):
    mp3 = enum.auto()
    # high quality mp3: for services whose native mp3 is low bitrate (Google and Gemini),
    # lossless audio is retrieved and re-encoded locally at constants.AUDIO_MP3_HQ_ENCODE_BITRATE_KBPS.
    # the file written to the collection is a regular .mp3
    mp3_hq = enum.auto()
    ogg_opus = enum.auto()
    ogg_vorbis = enum.auto()
