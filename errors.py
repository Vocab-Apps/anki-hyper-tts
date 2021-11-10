import sys
import logging
if hasattr(sys, '_pytest_mode'):
    import constants
else:
    from . import constants

# all exceptions inherit from this one
class LanguageToolsError(Exception):
    pass

# when something we expected to find is not found, like a deck, model, or field
# can happen when language mapping is not updated to reflect note type changes
class AnkiItemNotFoundError(LanguageToolsError):
    pass

class AnkiNoteEditorError(LanguageToolsError):
    pass

class LanguageMappingError(LanguageToolsError):
    pass

class FieldNotFoundError(AnkiItemNotFoundError):
    def __init__(self, dntf):
        message = f'Field not found: <b>{dntf}</b>. {constants.DOCUMENTATION_EDIT_RULES}'
        super().__init__(message)    

class FieldLanguageMappingError(LanguageMappingError):
    def __init__(self, dntf):
        message = f'No language set for {dntf}. {constants.DOCUMENTATION_PERFORM_LANGUAGE_MAPPING}'
        super().__init__(message)

class FieldLanguageSpecialMappingError(LanguageMappingError):
    def __init__(self, dntf, language_code):
        message = f'<b>{dntf}</b> is mapped to <b>{language_code}</b>. {constants.DOCUMENTATION_SPECIAL_LANGUAGE}'
        super().__init__(message)

class LanguageToolsValidationFieldEmpty(LanguageToolsError):
    def __init__(self):
        message = f'Field is empty'
        super().__init__(message)    

class NoVoiceSetError(LanguageToolsError):
    def __init__(self, language_name):
        message = f'No voice set for {language_name}. {constants.DOCUMENTATION_VOICE_SELECTION}'
        super().__init__(message)

class LanguageToolsRequestError(LanguageToolsError):
    pass

class AudioLanguageToolsRequestError(LanguageToolsRequestError):
    pass

class VoiceListRequestError(LanguageToolsRequestError):
    pass


# these ActionContext objects implement the "with " interface and help catch exceptions

class SingleActionContext():
    def __init__(self, error_manager, action):
        self.error_manager = error_manager
        self.action = action

    def __enter__(self):
        pass

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_value != None:
            if isinstance(exception_value, LanguageToolsError):
                self.error_manager.report_single_exception(exception_value, self.action)
            else:
                self.error_manager.report_unknown_exception_interactive(exception_value, self.action)
            return True
        return False

class BatchActionContext():
    def __init__(self, batch_error_manager, action):
        self.batch_error_manager = batch_error_manager
        self.action = action

    def __enter__(self):
        pass

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_value != None:
            if isinstance(exception_value, LanguageToolsError):
                self.batch_error_manager.report_batch_exception(exception_value, self.action)
            else:
                self.batch_error_manager.report_unknown_exception(exception_value, self.action)
            return True
        # no error, report success
        self.batch_error_manager.report_success(self.action)
        return False

class BatchErrorManager():
    def __init__(self, error_manager, batch_action):
        self.error_manager = error_manager
        self.batch_action = batch_action
        self.action_stats = {}

    def get_batch_action_context(self, action):
        return BatchActionContext(self, action)

    def init_action(self, action):
        if action not in self.action_stats:
            self.action_stats[action] = {
                'success': 0,
                'error': {}
            }

    def report_success(self, action):
        self.init_action(action)
        self.action_stats[action]['success'] = self.action_stats[action]['success'] + 1

    def track_error_stats(self, error_key, action):
        self.init_action(action)
        error_count = self.action_stats[action]['error'].get(error_key, 0)
        self.action_stats[action]['error'][error_key] = error_count + 1

    def report_batch_exception(self, exception, action):
        self.track_error_stats(str(exception), action)

    def report_unknown_exception(self, exception, action):
        error_key = f'Unknown Error: {str(exception)}'
        self.track_error_stats(error_key, action)
        self.error_manager.report_unknown_exception_batch(exception)

    # producing a human-readable error message
    
    def action_stats_error_str(self, action_errors):
        error_list = []
        for error_key, error_count in action_errors.items():
            error_list.append(f"""{error_key}: {error_count}""")
        return ', '.join(error_list)

    def action_stats_str(self, action_name, action_data):
        error_str = ' '
        if len(action_data['error']) > 0:
            error_str = ', errors: (' + self.action_stats_error_str(action_data['error']) + ')'
        return f"""<b>{action_name}</b>: success: {action_data['success']}{error_str}"""

    def get_stats_str(self):
        action_html_list = [f'<b>Finished {self.batch_action}.</b><br/>']
        for action, action_data in self.action_stats.items():
            action_html_list.append(self.action_stats_str(action, action_data))
        action_html = '<br/>\n'.join(action_html_list)
        return action_html

    def display_stats(self, parent):
        # build string then display stats
        self.error_manager.anki_utils.info_message(self.get_stats_str(), parent)


class ErrorManager():
    def __init__(self, anki_utils):
        self.anki_utils = anki_utils

    def report_single_exception(self, exception, action):
        self.anki_utils.report_known_exception_interactive(exception, action)

    def report_unknown_exception_interactive(self, exception, action):
        self.anki_utils.report_unknown_exception_interactive(exception, action)

    def report_unknown_exception_batch(self, exception):
        self.anki_utils.report_unknown_exception_background(exception)

    def get_single_action_context(self, action):
        return SingleActionContext(self, action)

    def get_batch_error_manager(self, batch_action):
        return BatchErrorManager(self, batch_action)
