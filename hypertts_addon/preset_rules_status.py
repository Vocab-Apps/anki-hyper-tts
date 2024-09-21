from . import constants
from . import config_models
from . import logging_utils
from . import errors
logger = logging_utils.get_child_logger(__name__)

# the code here keeps track of the success/failure of each preset
# when they are applied of previewd from the editor,
# or from the preset mapping rules screen

class RuleActionContext():
    def __init__(self, status, rule, anki_utils):
        self.anki_utils = anki_utils
        self.status = status
        self.rule = rule
        self.preset = None
        self.success = None # undefined
        self.exception = None

    def set_preset(self, preset: config_models.BatchConfig):
        self.preset = preset
        self.status.update_progress()

    def __str__(self):
        # use preset id by default, or name if available
        preset_name = self.rule.preset_id
        if self.preset != None:
            preset_name = self.preset.name
        
        # rule status.
        rule_status = 'creating audio...'
        if self.success != None:
            # task has completed
            if self.success:
                rule_status = f'<b style="color: {self.anki_utils.get_green_css_color()};">OK</b>'
            else:
                rule_status = f'<b style="color: {self.anki_utils.get_red_css_color()};">Error:</b> {str(self.exception)}'

        result = f'{preset_name}: {rule_status}'
        return result

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_value != None:
            if isinstance(exception_value, errors.HyperTTSError):
                # this is a known exception. capture it.
                self.exception = exception_value
                self.success = False
                self.status.update_progress()
                return True
            else:
                # unknown exception, don't intercept it
                return False
        self.success = True
        self.status.update_progress()
        return False

class PresetRulesStatus():
    def __init__(self, action_str, anki_utils):
        self.action_str = action_str
        self.anki_utils = anki_utils
        self.rule_action_context_list = []

    def get_rule_action_context(self, rule) -> RuleActionContext:
        action_context =  RuleActionContext(self, rule, self.anki_utils)
        self.rule_action_context_list.append(action_context)
        return action_context

    def __str__(self):
        progress_updates = [str(action_context) for action_context in self.rule_action_context_list]
        joined_updates = '<br/>'.join(progress_updates)
        result = f'<b>{constants.ADDON_NAME}: {self.action_str} Preset Rules:</b><br/>{joined_updates}'
        return result

    def update_progress(self):
        self.anki_utils.display_preset_rules_status(self)