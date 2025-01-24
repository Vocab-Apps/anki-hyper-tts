import enum

ENV_VAR_ANKI_LANGUAGE_TOOLS_BASE_URL = 'ANKI_LANGUAGE_TOOLS_BASE_URL'

ENABLE_SENTRY_CRASH_REPORTING = True

LOGGER_NAME = 'hypertts'
LOGGER_NAME_TEST = 'test_hypertts'

# requests related constants
RequestTimeout = 20 # 20 seconds max

CLOUDLANGUAGETOOLS_API_BASE_URL = 'https://cloudlanguagetools-api.vocab.ai'
VOCABAI_API_BASE_URL = 'https://app.vocab.ai/languagetools-api/v2'

class ServiceType(enum.Enum):
    dictionary = ("Dictionary, contains recordings of words.")
    tts = ("Text To Speech, can generate audio for full sentences.")
    def __init__(self, description):
        self.description = description

class ServiceFee(enum.Enum):
    free = enum.auto()
    paid = enum.auto()

class AudioRequestReason(enum.Enum):
    preview = enum.auto()
    batch = enum.auto()
    realtime = enum.auto()
    editor_browser = enum.auto()
    editor_add = enum.auto()

# what triggered this request (batch / on the fly / editor)
class RequestMode(enum.Enum):
    batch = enum.auto()
    dynamic = enum.auto()
    edit = enum.auto()

# batch modes
class BatchMode(enum.Enum):
    simple = enum.auto()
    template = enum.auto()
    advanced_template = enum.auto()

class TemplateFormatVersion(enum.Enum):
    v1 = enum.auto()

class VoiceSelectionMode(enum.Enum):
    single = enum.auto() # a single voice is selected
    random = enum.auto() # a random voice is selected, with optional weights
    priority = enum.auto() # the first voice is selected, and if audio is not found, move to the second one

class BatchNoteStatus(enum.Enum):
    Waiting = enum.auto()
    Processing = enum.auto()
    Done = enum.auto()
    Error = enum.auto()
    OK = enum.auto()

class TextReplacementRuleType(enum.Enum):
    Simple = enum.auto()
    Regex = enum.auto()

class RealtimeSourceType(enum.Enum):
    AnkiTTSTag = enum.auto()

class AnkiTTSFieldType(enum.Enum):
    Regular = enum.auto()
    Cloze = enum.auto()
    ClozeOnly = enum.auto()

class AnkiCardSide(enum.Enum):
    Front = enum.auto()
    Back = enum.auto()

class MappingRuleType(enum.Enum):
    NoteType = enum.auto()
    DeckNoteType = enum.auto()

DIR_HYPERTTS_ADDON = 'hypertts_addon'
DIR_SERVICES = 'services'

ANKIWEB_ADDON_ID = '111623432'

CONFIG_ADDON_NAME = 'anki-hyper-tts'
if ANKIWEB_ADDON_ID in __file__:
    CONFIG_ADDON_NAME = ANKIWEB_ADDON_ID


CONFIG_SCHEMA = 'config_schema'
CONFIG_SCHEMA_VERSION = 4
# deprecated, use CONFIG_PRESETS
CONFIG_BATCH_CONFIG = 'batch_config'
# this is the new config category, contains dict of uuids
CONFIG_PRESETS = 'presets'
CONFIG_DEFAULT_PRESETS = 'default_presets'
CONFIG_MAPPING_RULES = 'mapping_rules'
CONFIG_REALTIME_CONFIG = 'realtime_config'
CONFIG_CONFIGURATION = 'configuration'
CONFIG_PREFERENCES = 'preferences'
CONFIG_KEYBOARD_SHORTCUTS = 'keyboard_shortcuts'
CONFIG_LAST_USED_BATCH = 'last_used_batch'
CONFIG_USE_SELECTION = 'use_selection' # whether to use the selected portion of the field

ADDON_NAME = 'HyperTTS'
MENU_PREFIX = ADDON_NAME + ':'
TITLE_PREFIX = ADDON_NAME + ': '

GUI_EASY_DIALOG_TITLE = TITLE_PREFIX + 'Add Audio (Easy)'
GUI_COLLECTION_DIALOG_TITLE = TITLE_PREFIX + 'Add Audio (Collection)'
GUI_REALTIME_DIALOG_TITLE = TITLE_PREFIX + 'Add Audio (Realtime)'
GUI_CONFIGURATION_DIALOG_TITLE = TITLE_PREFIX + 'Configuration'
GUI_PREFERENCES_DIALOG_TITLE = TITLE_PREFIX + 'Preferences'
GUI_CHOOSE_PRESET_DIALOG_TITLE = TITLE_PREFIX + 'Choose Preset'
GUI_PRESET_MAPPING_RULES_DIALOG_TITLE = TITLE_PREFIX + 'Preset Rules'

DIALOG_ID_CHOOSE_PRESET = 'choose_preset'
DIALOG_ID_BATCH = 'batch'
DIALOG_ID_PRESET_MAPPING_RULES = 'preset_mapping_rules'
DIALOG_ID_EASY = 'easy'
DIALOG_ID_CHDOOSE_EASY_ADVANCED = 'choose_easy_advanced'

TTS_TAG_VOICE = 'HyperTTS'
TTS_TAG_HYPERTTS_PRESET = 'hypertts_preset'

PYCMD_ADD_AUDIO = 'addaudio'
PYCMD_PREVIEW_AUDIO = 'previewaudio'

PYCMD_ADD_AUDIO_PREFIX = f'hypertts:{PYCMD_ADD_AUDIO}:'
PYCMD_PREVIEW_AUDIO_PREFIX = f'hypertts:{PYCMD_PREVIEW_AUDIO}:'

UNDO_ENTRY_NAME = ADDON_NAME + ': Add Audio to Notes'
UNDO_ENTRY_ADD_TTS_TAG = ADDON_NAME + ': Configure Realtime TTS Tag'

GREEN_COLOR_REGULAR = '#69F0AE'
RED_COLOR_REGULAR = '#FFCDD2'

GREEN_STYLESHEET = f'background-color: {GREEN_COLOR_REGULAR};'
RED_STYLESHEET = f'background-color: {RED_COLOR_REGULAR};'

GREEN_COLOR_NIGHTMODE = '#1B5E20'
RED_COLOR_NIGHTMODE = '#B71C1C'

GREEN_STYLESHEET_NIGHTMODE = f'background-color: {GREEN_COLOR_NIGHTMODE};'
RED_STYLESHEET_NIGHTMODE = f'background-color: {RED_COLOR_NIGHTMODE};'

LABEL_FILTER_ALL = 'All'

BATCH_CONFIG_NEW = 'New Preset'

GUI_TEXT_UNKNOWN_PRESET = 'Unknown Preset'

GUI_TEXT_MAPPING_RULES = ("""<i>Here, you can configure presets specific to this note or deck."""
""" You will be able to preview or add audio with a single click of the play/preview buttons on the Anki note editor."""
""" You can associate a preset with the Note Type (the preset applies to all notes of that type)"""
""" or with the Deck And Note Type (the preset only applies to this note type + deck combination)"""
)

GUI_TEXT_SOURCE_MODE = """Choose a source mode:
<b>Simple:</b> your text comes from a single field. In most cases, choose this option.
<b>Template:</b> text from different fields can be combined together.
<b>Advanced Template:</b> fields can be combined in complex ways using Python."""

GUI_TEXT_SOURCE_FIELD_NAME = """Source Field:"""
GUI_TEXT_SOURCE_USE_SELECTION = """If text is selected, use selection instead of the full field."""
GUI_TEXT_SOURCE_SIMPLE_TEMPLATE = """Enter template using syntax {Field1} {Field2}:"""
GUI_TEXT_SOURCE_ADVANCED_TEMPLATE = """Enter template using Python syntax (advanced users only):
a simple example:
field_1 = template_fields['Field 1']
field_2 = template_fields['Field 2']
result = f'{field_1} {field_2}'
"""


GUI_TEXT_SOURCE_MODE_REALTIME = """Choose a source mode:
<b>AnkiTTSTag:</b> Configure Realtime Audio using Anki {{tts}} tag. You can choose a single field""" \
""" containing the source text. Will use HyperTTS when reviewing on desktop and fallback to other voices on iOS AnkiMobile."""

GUI_TEXT_SOURCE_FIELD_TYPE_REALTIME = """Field Type:
<b>Regular:</b> the field should be pronounced in its entirety.
<b>Cloze:</b> only use this for cloze fields. The audio on the front will contain everything except for the hidden word"""\
""" (which you have to guess), and the audio on the back will contain everything.
<b>ClozeOnly:</b> only use this for cloze fields. Only the hidden word will be pronounced, and nothing else."""\
"""It only makes to use this on the back side."""


GUI_TEXT_EASY_SOURCE_SELECTION_NO_TEXT = '<i>(no selected text)</i>'
GUI_TEXT_EASY_SOURCE_CLIPBOARD_NO_TEXT = '<i>(no clipboard text)</i>'
GUI_TEXT_EASY_SOURCE_FIELD_EMPTY = 'empty'

GUI_TEXT_EASY_SOURCE_FIELD = """<i>The sound will be generated using this text. You can edit it.</i>"""
GUI_TEXT_EASY_VOICE_SELECTION = """<i>Choose a voice. You can filter by Language and Service.</i>"""
GUI_TEXT_EASY_TARGET = """<i>Decide where the sound tag will be placed.</i>"""
GUI_TEXT_EASY_BUTTON_MORE_SETTINGS = 'More Settings...'
GUI_TEXT_EASY_BUTTON_HIDE_MORE_SETTINGS = 'Hide Settings...'

GUI_TEXT_EASY_MODE_LABEL_PRESET_MAPPING_RULES = '<i>Enable to use a simplified, easier interface when adding audio to a single note in the Anki editor.</i>'
 
GUI_TEXT_CHOICE_EASY_ADVANCED_EXPLANATION = """Please choose how you want to add audio in the Anki editor."""
GUI_TEXT_CHOICE_EASY_MODE = """Simple interface for adding audio manually. Just choose the field \
and the voice to add audio. Similar to AwesomeTTS. Choose this if you want something simple."""
GUI_TEXT_CHOICE_ADVANCED_MODE = """Full interface with all settings, allows you to add sound manually \
or automatically. You can setup presets for different note types or decks. Choose this if you \
don't mind configuring settings and setup presets."""
GUI_TEXT_CHOICE_EASY_ADVANCED_BOTTOM = """<i>You can change this setting later by clicking the gear button on the editor button bar (Configure preset rules)</i>"""

GUI_TEXT_TARGET_FIELD = """Sound tags will be inserted in this field"""

GUI_TEXT_TARGET_TEXT_AND_SOUND = """<i>Should the target field only contain the sound tag, or should
it contain both text and sound tag.</i>"""
GUI_TEXT_TARGET_REMOVE_SOUND_TAG = """<i>If the target field already contains a sound tag, should it get  removed?</i>"""

GUI_TEXT_BATCH_COMPLETED = """<b>Finished adding Audio to notes</b>. You can undo this operation in menu Edit, 
Undo HyperTTS: Add Audio to Notes. You may close this dialog.
"""

GUI_TEXT_HYPERTTS_PRO = """HyperTTS Pro gives you access to <b>all premium TTS services</b>."""\
""" Azure, Google, Amazon, Watson and others. Over <b>1200 voices, 60+ languages</b>. """ +\
""""""

GUI_TEXT_BUTTON_TRIAL = """Free Trial"""
GUI_TEXT_BUTTON_API_KEY = """Enter API Key"""
GUI_TEXT_BUTTON_BUY = """Sign Up"""

BUY_PLAN_URL = """https://www.vocab.ai/hypertts-pro?utm_campaign=hypertts_config&utm_source=hypertts&utm_medium=addon"""

GUI_TEXT_HYPERTTS_PRO_TRIAL = """Free Trial access instantly, just enter your email."""
GUI_TEXT_HYPERTTS_PRO_BUY_PLAN = """Subscribe to HyperTTS Pro. Get access in 5mn."""
GUI_TEXT_HYPERTTS_PRO_ENTER_API_KEY = """Enter HyperTTS Pro / AwesomeTTS Plus / Language Tools API Key."""

GUI_TEXT_HYPERTTS_PRO_ENABLED = """<b>HyperTTS Pro Enabled</b>"""
GUI_TEXT_HYPERTTS_PRO_TRIAL_ENTER_EMAIL = """Enter your email to get trial access instantly. """\
"""Try all <b>1200 premium voices, 60+ languages</b>. Trial quota of 5,000 characters."""

GUI_TEXT_REALTIME_SINGLE_NOTE = """Please select a single note to add Realtime Audio"""
GUI_TEXT_REALTIME_CHOOSE_TEMPLATE = """Choose card template"""
GUI_TEXT_REALTIME_REMOVED_TAG = """Removed TTS Tag. Realtime audio will not play anymore."""

GUI_TEXT_SHORTCUTS_ANKI_RESTART = """Note: You'll need to restart Anki after modifying these shortcuts."""

GUI_TEXT_SHORTCUTS_EDITOR_ADD_AUDIO = """Add Audio to note using the selected preset"""
GUI_TEXT_SHORTCUTS_EDITOR_PREVIEW_AUDIO = """Preview Audio for a note using the selected preset"""

GUI_TEXT_ERROR_HANDLING_REALTIME_TTS = """How to display errors during Realtime TTS"""

GRAPHICS_PRO_BANNER = 'hypertts_pro_banner.png'
GRAPHICS_LITE_BANNER = 'hypertts_lite_banner.png'
GRAPHICS_SERVICE_COMPATIBLE = 'hypertts_service_compatible_banner.png'
GRAPHICS_SERVICE_ENABLED = 'hypertts_service_enabled_banner.png'

TEXT_PROCESSING_DEFAULT_HTMLTOTEXTLINE = True
TEXT_PROCESSING_DEFAULT_STRIP_BRACKETS = False
TEXT_PROCESSING_DEFAULT_SSML_CHARACTERS = True
TEXT_PROCESSING_DEFAULT_REPLACE_AFTER = True
TEXT_PROCESSING_DEFAULT_IGNORE_CASE = False

# prevent message boxes from getting too big
MESSAGE_TEXT_MAX_LENGTH = 500

CLIENT_NAME = 'hypertts'

class ReplaceType(enum.Enum):
    simple = enum.auto()
    regex = enum.auto()

class Gender(enum.Enum):
    Male = enum.auto()
    Female = enum.auto()
    Any = enum.auto()

class ErrorDialogType(str, enum.Enum):
    Dialog = 'Dialog'
    Tooltip = 'Tooltip'
    Nothing = 'Nothing'

