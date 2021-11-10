import enum

ENV_VAR_ANKI_LANGUAGE_TOOLS_BASE_URL = 'ANKI_LANGUAGE_TOOLS_BASE_URL'
CONFIG_DECK_LANGUAGES = 'deck_languages'
CONFIG_WANTED_LANGUAGES = 'wanted_languages'
CONFIG_BATCH_TRANSLATION = 'batch_translations'
CONFIG_BATCH_TRANSLITERATION = 'batch_transliterations'
CONFIG_BATCH_AUDIO = 'batch_audio'
CONFIG_VOICE_SELECTION = 'voice_selection'
CONFIG_APPLY_UPDATES_AUTOMATICALLY = 'apply_updates_automatically'
CONFIG_LIVE_UPDATE_DELAY = 'live_update_delay'
CONFIG_TEXT_PROCESSING = 'text_processing'
ADDON_NAME = 'Language Tools'
MENU_PREFIX = ADDON_NAME + ':'
DEFAULT_LANGUAGE = 'en' # always add this language, even if the user didn't add it themselves
EDITOR_WEB_FIELD_ID_TRANSLATION = 'translation'

GREEN_STYLESHEET = 'background-color: #69F0AE;'
RED_STYLESHEET = 'background-color: #FFCDD2;'

GREEN_STYLESHEET_NIGHTMODE = 'background-color: #2E7D32;'
RED_STYLESHEET_NIGHTMODE = 'background-color: #B71C1C;'

DOCUMENTATION_PERFORM_LANGUAGE_MAPPING = 'Please setup Language Mappings, from the Anki main screen: <b>Tools -> Language Tools: Language Mapping</b>'
DOCUMENTATION_EDIT_RULES = 'Please edit rules by selecting a note and clicking <b>Language Tools -> Show Rules for Selected Notes</b>'
DOCUMENTATION_SPECIAL_LANGUAGE = 'You cannot generate audio/translations/transliterations from this field. Please select an actual language, from the Anki main screen: <b>Tools -> Language Tools: Language Mapping</b>'
DOCUMENTATION_VOICE_SELECTION = 'Please select a voice, from the Anki main screen: <b>Tools -> Language Tools: Voice Selection</b>'

CLIENT_NAME = 'languagetools'

class TransformationType(enum.Enum):
    Translation = enum.auto()
    Transliteration = enum.auto()
    Audio = enum.auto()

class ReplaceType(enum.Enum):
    simple = enum.auto()
    regex = enum.auto()

# these are special languages that we store on a field level, which don't allow translating to/from
class SpecialLanguage(enum.Enum):
    transliteration = enum.auto()
    sound = enum.auto()