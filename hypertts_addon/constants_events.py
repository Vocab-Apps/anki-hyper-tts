import enum

# events reporting
# ================

PREFIX = 'anki_addon_v1'
ADDON = 'hypertts'

GENERATE_MAX_EVENTS = 5

# contexts
class EventContext(enum.Enum):
    addon = enum.auto()
    services = enum.auto()
    hyperttspro = enum.auto()
    generate = enum.auto()
    voice_selection = enum.auto()
    choose_easy_advanced = enum.auto()
    servicemanager = enum.auto()

# events
class Event(enum.Enum):
    open = enum.auto()
    close = enum.auto()
    click_cancel = enum.auto()
    click_save = enum.auto()
    click_add = enum.auto()
    click_preview = enum.auto()
    install = enum.auto()
    choose = enum.auto()
    # dialog-specific
    click_disable_all_services = enum.auto()
    click_enable_free_services = enum.auto()
    click_free_trial = enum.auto()
    click_enter_api_key = enum.auto()
    click_sign_up = enum.auto()
    click_free_trial_ok = enum.auto()
    click_free_trial_confirm = enum.auto()
    # backend
    get_tts_audio = enum.auto()
    error = enum.auto()

class EventMode(enum.Enum):
    advanced_browser_existing_preset = enum.auto()
    advanced_browser_new_preset = enum.auto()
    advanced_editor_existing_preset = enum.auto()
    advanced_editor_new_preset = enum.auto()
    easy_editor = enum.auto()
    easy_mode = enum.auto()
    advanced_mode = enum.auto()