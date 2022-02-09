import enum

ENV_VAR_ANKI_LANGUAGE_TOOLS_BASE_URL = 'ANKI_LANGUAGE_TOOLS_BASE_URL'

ENABLE_SENTRY_CRASH_REPORTING = True

# requests related constants
RequestTimeout = 15 # 15 seconds max

class AudioRequestReason(enum.Enum):
    preview = enum.auto()

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

CONFIG_BATCH_CONFIG = 'batch_config'
CONFIG_REALTIME_CONFIG = 'realtime_config'
CONFIG_CONFIGURATION = 'configuration'

ADDON_NAME = 'HyperTTS'
MENU_PREFIX = ADDON_NAME + ':'
TITLE_PREFIX = ADDON_NAME + ': '

GUI_COLLECTION_DIALOG_TITLE = TITLE_PREFIX + 'Add Audio (Collection)'
GUI_REALTIME_DIALOG_TITLE = TITLE_PREFIX + 'Add Audio (Realtime)'
GUI_CONFIGURATION_DIALOG_TITLE = TITLE_PREFIX + 'Configuration'

TTS_TAG_HYPERTTS_PRESET = 'hypertts_preset'

PYCMD_ADD_AUDIO_PREFIX = 'hypertts:addaudio:'

UNDO_ENTRY_NAME = ADDON_NAME + ': Add Audio to Notes'

GREEN_STYLESHEET = 'background-color: #69F0AE;'
RED_STYLESHEET = 'background-color: #FFCDD2;'

GREEN_STYLESHEET_NIGHTMODE = 'background-color: #2E7D32;'
RED_STYLESHEET_NIGHTMODE = 'background-color: #B71C1C;'

LABEL_FILTER_ALL = 'All'

BATCH_CONFIG_NEW = 'New Preset'

GUI_TEXT_SOURCE_MODE = """Choose a source mode:
<b>Simple:</b> your text comes from a single field. In most cases, choose this option.
<b>Template:</b> text from different fields can be combined together.
<b>Advanced Template:</b> fields can be combined in complex ways using Python."""

GUI_TEXT_SOURCE_FIELD_NAME = """Source Field:"""
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


GUI_TEXT_TARGET_FIELD = """Sound tags will be inserted in this field"""

GUI_TEXT_TARGET_TEXT_AND_SOUND = """Should the target field only contain the sound tag, or should
it contain both text and sound tag."""
GUI_TEXT_TARGET_REMOVE_SOUND_TAG = """If the target field already contains a sound tag, should it get  removed?"""

GUI_TEXT_BATCH_COMPLETED = """<b>Finished adding Audio to notes</b>. You can undo this operation in menu Edit, 
Undo HyperTTS: Add Audio to Notes. You may close this dialog.
"""

GUI_TEXT_HYPERTTS_PRO = """HyperTTS Pro gives you access to all premium services.""" +\
""" (You can use the same API key as AwesomeTTS Plus / Language Tools)"""

GUI_TEXT_REALTIME_SINGLE_NOTE = """Please select a single note to add Realtime Audio"""
GUI_TEXT_REALTIME_CHOOSE_TEMPLATE = """Choose card template"""

GRAPHICS_PRO_BANNER = 'hypertts_pro_banner.png'
GRAPHICS_LITE_BANNER = 'hypertts_lite_banner.png'
GRAPHICS_SERVICE_COMPATIBLE = 'hypertts_service_compatible_banner.png'
GRAPHICS_SERVICE_ENABLED = 'hypertts_service_enabled_banner.png'

TEXT_PROCESSING_DEFAULT_HTMLTOTEXTLINE = True
TEXT_PROCESSING_DEFAULT_SSML_CHARACTERS = True
TEXT_PROCESSING_DEFAULT_REPLACE_AFTER = True

CLIENT_NAME = 'hypertts'

class ReplaceType(enum.Enum):
    simple = enum.auto()
    regex = enum.auto()

class Gender(enum.Enum):
    Male = enum.auto()
    Female = enum.auto()
    Any = enum.auto()

class VoiceOptionTypes(enum.Enum):
    number = enum.auto()

