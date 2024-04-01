import sys
import logging

constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)

logger = logging.getLogger(__name__)

# all known exceptions inherit from this one
class HyperTTSError(Exception):
    pass

class CollectionNotOpen(HyperTTSError):
    def __init__(self):
        message = "Anki Collection not open. Please ensure your Anki profile is loaded and that you can access your notes."
        super().__init__(message)    

class FieldNotFoundError(HyperTTSError):
    def __init__(self, field_name):
        message = f'Field <b>{field_name}</b> not found'
        super().__init__(message)    

class SourceFieldNotFoundError(HyperTTSError):
    def __init__(self, field_name):
        message = f'Source Field <b>{field_name}</b> not found'
        super().__init__(message)    


class TargetFieldNotFoundError(HyperTTSError):
    def __init__(self, field_name):
        message = f'Target Field <b>{field_name}</b> not found'
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

class AudioNotFoundError(HyperTTSError):
    def __init__(self, source_text, voice):
        message = f'Audio not found for [{source_text}] (voice: {voice})'
        super().__init__(message)
        self.source_text = source_text
        self.voice = voice

class AudioNotFoundAnyVoiceError(HyperTTSError):
    def __init__(self, source_text):
        message = f'Audio not found in any voices for [{source_text}]'
        super().__init__(message)
        self.source_text = source_text

class VoiceNotFound(HyperTTSError):
    def __init__(self, voice_data):
        message = f'Voice not found: {voice_data}]'
        super().__init__(message)
        self.voice_data = voice_data

class PresetNotFound(HyperTTSError):
    def __init__(self, preset_name):
        message = f'Preset not found: {preset_name}]'
        super().__init__(message)

class RealtimePresetNotFound(HyperTTSError):
    def __init__(self, preset_name):
        message = f'Realtime Preset not found: {preset_name}. Please remove, then re-add TTS tag.]'
        super().__init__(message)        


class MissingDirectory(HyperTTSError):
    def __init__(self, directory):
        message = f'Could not find directory {directory}, cannot generate audio files. Please check whether this directory exists.'
        super().__init__(message)        


class RequestError(HyperTTSError):
    def __init__(self, source_text, voice, error_message):
        message = f'Could not request audio for [{source_text}]: {error_message} (voice: {voice})'
        super().__init__(message)
        self.source_text = source_text
        self.voice = voice
        self.error_message = error_message

class NoVoiceSelected(HyperTTSError):
    def __init__(self):
        message = f'No voice selected. Please select a voice, you may need to update your filters.'
        super().__init__(message)

class NoVoicesAvailable(HyperTTSError):
    def __init__(self):
        message = f'No voices available. You may need to configure some services in the HyperTTS Configuration. ' \
            '<a href="https://www.vocab.ai/tutorials/hypertts-getting-started">Please follow this tutorial: getting started with HyperTTS</a>.'
        super().__init__(message)


class NoVoicesAdded(HyperTTSError):
    def __init__(self):
        message = f'No voices have been added. You must add at least one voice when in Random or Priority mode.'
        super().__init__(message)

class NoNotesSelected(HyperTTSError):
    def __init__(self):
        message = f'No notes have been selected. You must select at least one note from the browser.'
        super().__init__(message)

class NoNotesSelectedPreview(HyperTTSError):
    def __init__(self):
        message = f'No notes have been selected. Select one note to preview sound.'
        super().__init__(message)        

class NoPresetMappingRulesDefined(HyperTTSError):
    def __init__(self):
        message = ('You have not configured any preset mapping rules, '
        'please click the gear icon in the editor to add some, then you will be able to add / preview audio')
        super().__init__(message)        


# template expansion errors
class NoResultVar(HyperTTSError):
    def __init__(self):
        message = f'No "result" variable found. You must assign the final template output to a result variable.'
        super().__init__(message)

class TemplateExpansionError(HyperTTSError):
    def __init__(self, exception):
        message = f'Could not process template: {str(exception)}'
        super().__init__(message)

# TTS related errors
class TTSTagProcessingError(HyperTTSError):
    def __init__(self):
        message = f'Could not process TTS Tag, please re-add TTS tag by adding Realtime Audio to Note'
        super().__init__(message)

# model validation errors
# =======================

class ModelValidationError(HyperTTSError):
    def __init__(self, message):
        super().__init__(message)    

class PresetNameNotSet(ModelValidationError):
    def __init__(self):
        super().__init__('Name of preset is not set')

class SourceFieldNotSet(ModelValidationError):
    def __init__(self):
        super().__init__('Source Field is not set')

class SourceFieldTypeNotSet(ModelValidationError):
    def __init__(self):
        super().__init__('Source Field Type is not set')        

class SourceTemplateNotSet(ModelValidationError):
    def __init__(self):
        super().__init__('Source Template is not set')

class TargetFieldNotSet(ModelValidationError):
    def __init__(self):
        super().__init__('Target Field is not set')

class VoiceSelectionNotSet(ModelValidationError):
    def __init__(self):
        super().__init__('Voice Selection not done')

class TextProcessingNotSet(ModelValidationError):
    def __init__(self):
        super().__init__('Text Processing not set')        

class NoVoiceSet(ModelValidationError):
    def __init__(self):
        super().__init__('No Voice has been set')

# service configuration related errors
# ====================================

class MissingServiceConfiguration(HyperTTSError):
    def __init__(self, service_name, key):
        super().__init__(f'You must configure {key} for service {service_name}')

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

class SingleActionContextConfigurable():
    def __init__(self, error_manager, action: str, error_dialog_type: constants.ErrorDialogType):
        self.error_manager = error_manager
        self.action = action
        self.error_dialog_type = error_dialog_type

    def __enter__(self):
        pass

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_value != None:
            if isinstance(exception_value, HyperTTSError):
                self.error_manager.report_single_exception_dialog_type(exception_value, self.action, self.error_dialog_type)
            else:
                self.error_manager.report_unknown_exception_interactive(exception_value, self.action)
            return True
        return False        

class BatchActionContext():
    def __init__(self, batch_error_manager, note_id):
        self.batch_error_manager = batch_error_manager
        self.note_id = note_id

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

    def get_batch_action_context(self, note_id):
        return BatchActionContext(self, note_id)

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
        self.anki_utils.report_known_exception_interactive_dialog(exception, action)

    def report_single_exception_dialog_type(self, exception, action, error_dialog_type: constants.ErrorDialogType):
        if error_dialog_type == constants.ErrorDialogType.Dialog:
            self.anki_utils.report_known_exception_interactive_dialog(exception, action)
        elif error_dialog_type == constants.ErrorDialogType.Tooltip:
            self.anki_utils.report_known_exception_interactive_tooltip(exception, action)
        elif error_dialog_type == constants.ErrorDialogType.Nothing:
            pass
        else:
            logger.error(f'Unknown error dialog type: {error_dialog_type}')

    def report_unknown_exception_interactive(self, exception, action):
        self.anki_utils.report_unknown_exception_interactive(exception, action)

    def report_unknown_exception_batch(self, exception):
        self.anki_utils.report_unknown_exception_background(exception)

    def get_single_action_context(self, action):
        return SingleActionContext(self, action)

    def get_single_action_context_configurable(self, action, error_dialog_type: constants.ErrorDialogType):
        return SingleActionContextConfigurable(self, action, error_dialog_type)

    def get_batch_error_manager(self, batch_action):
        return BatchErrorManager(self, batch_action)
