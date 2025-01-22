import enum

# events reporting
# ================

PREFIX = 'anki_addon_v1'
ADDON = 'hypertts'

# contexts
class EventContext(enum.Enum):
    addon = enum.auto()
    services = enum.auto()
    hyperttspro = enum.auto()

# events
class Event(enum.Enum):
    open = enum.auto()
    click_cancel = enum.auto()
    click_save = enum.auto()
    # dialog-specific
    click_disable_all_services = enum.auto()
    click_enable_free_services = enum.auto()
    click_free_trial = enum.auto()
    click_enter_api_key = enum.auto()
    click_sign_up = enum.auto()
    click_free_trial_ok = enum.auto()
    click_free_trial_confirm = enum.auto()
