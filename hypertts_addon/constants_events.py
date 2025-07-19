import enum

# events reporting
# ================

PREFIX = 'anki_addon_v2'
ADDON = 'hypertts'

GENERATE_MAX_EVENTS = 5

# feature flags
FEATURE_FLAG_DEFAULT_VALUE = 'control'

STATS_DAYS_CUTOFF=14  # days after install to enable stats

# contexts
class EventContext(enum.Enum):
    addon = enum.auto()
    services = enum.auto()
    hyperttspro = enum.auto()
    trial_signup = enum.auto()
    generate = enum.auto()
    voice_selection = enum.auto()
    choose_easy_advanced = enum.auto()
    servicemanager = enum.auto()
    services_configuration = enum.auto()

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
    click_enter_api_key = enum.auto() # to be replaced
    click_remove_api_key = enum.auto()
    click_sign_up = enum.auto()
    click_free_trial_ok = enum.auto() # to be replaced
    click_welcome_configure_services = enum.auto()
    click_welcome_add_audio = enum.auto()
    # trial related
    click_trial_signup = enum.auto()
    trial_signup_error = enum.auto()
    trial_signup_success = enum.auto()
    click_email_verification_status = enum.auto()
    email_verification_success = enum.auto()
    email_verification_failure = enum.auto()
    click_how_to_add_audio = enum.auto()
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
