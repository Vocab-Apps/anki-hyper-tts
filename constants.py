import enum

ENV_VAR_ANKI_LANGUAGE_TOOLS_BASE_URL = 'ANKI_LANGUAGE_TOOLS_BASE_URL'

# batch modes
class BatchMode(enum.Enum):
    simple = enum.auto()
    template = enum.auto()
    raw_ssml_template = enum.auto()

#
CONFIG_BATCH_TEXT_AND_SOUND_TAG = 'text_and_sound_tag'

CONFIG_BATCH_AUDIO = 'batch_audio'

CONFIG_TEXT_PROCESSING = 'text_processing'
ADDON_NAME = 'HyperTTS'
MENU_PREFIX = ADDON_NAME + ':'

GREEN_STYLESHEET = 'background-color: #69F0AE;'
RED_STYLESHEET = 'background-color: #FFCDD2;'

GREEN_STYLESHEET_NIGHTMODE = 'background-color: #2E7D32;'
RED_STYLESHEET_NIGHTMODE = 'background-color: #B71C1C;'

DOCUMENTATION_PERFORM_LANGUAGE_MAPPING = 'Please setup Language Mappings, from the Anki main screen: <b>Tools -> Language Tools: Language Mapping</b>'
DOCUMENTATION_EDIT_RULES = 'Please edit rules by selecting a note and clicking <b>Language Tools -> Show Rules for Selected Notes</b>'
DOCUMENTATION_SPECIAL_LANGUAGE = 'You cannot generate audio/translations/transliterations from this field. Please select an actual language, from the Anki main screen: <b>Tools -> Language Tools: Language Mapping</b>'
DOCUMENTATION_VOICE_SELECTION = 'Please select a voice, from the Anki main screen: <b>Tools -> Language Tools: Voice Selection</b>'

CLIENT_NAME = 'hypertts'

class ReplaceType(enum.Enum):
    simple = enum.auto()
    regex = enum.auto()

# these are special languages that we store on a field level, which don't allow translating to/from
class SpecialLanguage(enum.Enum):
    transliteration = enum.auto()
    sound = enum.auto()