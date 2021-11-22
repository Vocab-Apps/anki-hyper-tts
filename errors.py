import sys
import logging
if hasattr(sys, '_pytest_mode'):
    import constants
else:
    from . import constants

# all known exceptions inherit from this one
class HyperTTSError(Exception):
    pass

class FieldNotFoundError(HyperTTSError):
    def __init__(self, field_name):
        message = f'Field <b>{field_name}</b> not found'
        super().__init__(message)    

class FieldEmptyError(HyperTTSError):
    def __init__(self, field_name):
        message = f'Field <b>{field_name}</b> is empty'
        super().__init__(message)    

class SourceTextEmpty(HyperTTSError):
    def __init__(self):
        message = 'Source text is empty'
        super().__init__(message)    

class TextReplacementError(HyperTTSError):
    def __init__(self, text, pattern, replacement, error_msg):
        message = f'Could not process text replacement (pattern: {pattern}, replacement: {replacement}, text: {text}): {error_msg}'
        super().__init__(message)

class RequestError(HyperTTSError):
    def __init__(self, source_text, voice, error_message):
        message = f'Could not request audio for [{source_text}]: {error_message} (voice: {voice})'
        super().__init__(message)
        self.source_text = source_text
        self.voice = voice
        self.error_message = error_message

# these ActionContext objects implement the "with " interface and help catch exceptions

class SingleActionContext():
    def __init__(self, error_manager, action):
        self.error_manager = error_manager
        self.action = action

    def __enter__(self):
        pass

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_value != None:
            if isinstance(exception_value, HyperTTSError):
                self.error_manager.report_single_exception(exception_value, self.action)
            else:
                self.error_manager.report_unknown_exception_interactive(exception_value, self.action)
            return True
        return False

class BatchActionContext():
    def __init__(self, batch_error_manager):
        self.batch_error_manager = batch_error_manager

    def __enter__(self):
        pass

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_value != None:
            if isinstance(exception_value, HyperTTSError):
                self.batch_error_manager.report_batch_exception(exception_value)
            else:
                self.batch_error_manager.report_unknown_exception(exception_value)
            return True
        # no error, report success
        self.batch_error_manager.report_success()
        return False

class BatchErrorManager():
    def __init__(self, error_manager, batch_action):
        self.error_manager = error_manager
        self.batch_action = batch_action
        self.action_stats = {
            'success': 0,
            'error': {}
        }
        self.iteration_count = 0

    def get_batch_action_context(self):
        return BatchActionContext(self)

    def report_success(self):
        self.action_stats['success'] += 1
        self.iteration_count += 1

    def track_error_stats(self, error_key):
        error_count = self.action_stats['error'].get(error_key, 0)
        self.action_stats['error'][error_key] = error_count + 1
        self.iteration_count += 1        

    def report_batch_exception(self, exception):
        self.track_error_stats(str(exception))

    def report_unknown_exception(self, exception):
        error_key = f'Unknown Error: {str(exception)}'
        self.track_error_stats(error_key)
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
