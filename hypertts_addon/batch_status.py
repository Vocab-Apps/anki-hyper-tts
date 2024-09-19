import sys

from . import constants
from . import errors
from . import logging_utils
logger = logging_utils.get_child_logger(__name__)

class NoteStatus():
    def __init__(self, note_id):
        self.note_id = note_id
        self.source_text = None
        self.processed_text = None
        self.sound_file = None
        self.error = None
        self.status = None

class BatchNoteActionContext():
    def __init__(self, batch_status, note_id):
        self.batch_status = batch_status
        self.note_id = note_id

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_value != None:
            if isinstance(exception_value, errors.HyperTTSError):
                self.batch_status.report_known_error(self.note_id, exception_value)
            else:
                self.batch_status.report_unknown_exception(self.note_id, exception_value)
            self.batch_status.notify_change(self.note_id)
            return True
        self.batch_status.notify_change(self.note_id)
        return False    

    def set_sound(self, sound_file):
        self.batch_status.set_sound_file(self.note_id, sound_file)

    def set_source_text(self, source_text):
        self.batch_status.set_source_text(self.note_id, source_text)

    def set_processed_text(self, processed_text):
        self.batch_status.set_processed_text(self.note_id, processed_text)

    def set_status(self, status):
        self.batch_status.set_status(self.note_id, status)

class BatchRunningActionContext():
    def __init__(self, batch_status):
        self.batch_status = batch_status

    def __enter__(self):
        self.batch_status.task_running = True
        self.batch_status.must_continue = True
        self.batch_status.notify_start()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.batch_status.task_running = False
        completed = self.batch_status.must_continue
        self.batch_status.notify_end(completed)
        return False        

class BatchStatus():
    def __init__(self, anki_utils, note_id_list, change_listener):
        self.anki_utils = anki_utils
        self.note_id_list = note_id_list
        self.change_listener = change_listener
        self.note_status_array = []
        self.note_status_map = {}
        self.note_id_map = {}
        self.task_running = False
        self.must_continue = False
        i = 0
        for note_id in self.note_id_list:
            note_status = NoteStatus(note_id)
            self.note_status_array.append(note_status)
            self.note_status_map[note_id] = note_status
            self.note_id_map[note_id] = i
            i += 1
    
    def is_running(self):
        return self.task_running

    def stop(self):
        logger.info('stopping current batch')
        self.must_continue = False

    def __getitem__(self, array_index):
        return self.note_status_array[array_index]

    def get_batch_running_action_context(self):
        return BatchRunningActionContext(self)

    def get_note_action_context(self, note_id, blank_fields):
        note_status = self.note_status_map[note_id]
        note_status.error = None
        note_status.status = constants.BatchNoteStatus.Processing
        if blank_fields:
            note_status.source_text = None
            note_status.processed_text = None
            note_status.sound_file = None
        return BatchNoteActionContext(self, note_id)

    # error reporting

    def report_known_error(self, note_id, exception_value):
        self.note_status_map[note_id].status = constants.BatchNoteStatus.Error
        self.note_status_map[note_id].error = exception_value
        self.notify_change(note_id)

    def report_unknown_exception(self, note_id, exception_value):
        self.note_status_map[note_id].status = constants.BatchNoteStatus.Error
        self.note_status_map[note_id].error = exception_value
        self.anki_utils.report_unknown_exception_background(exception_value)
        self.notify_change(note_id)

    # set the various fields on the NoteStatus

    def set_source_text(self, note_id, source_text):
        self.note_status_map[note_id].source_text = source_text
        self.notify_change(note_id)

    def set_processed_text(self, note_id, processed_text):
        self.note_status_map[note_id].processed_text = processed_text
        self.notify_change(note_id)

    def set_sound_file(self, note_id, sound_file):
        self.note_status_map[note_id].sound_file = sound_file
        self.notify_change(note_id)

    def set_status(self, note_id, status):
        self.note_status_map[note_id].status = status
        self.notify_change(note_id)

    def notify_start(self):
        self.start_time = self.anki_utils.get_current_time()
        self.change_listener.batch_start()

    def notify_change(self, note_id):
        row = self.note_id_map[note_id]
        self.change_listener.batch_change(note_id, row, len(self.note_id_list), self.start_time, self.anki_utils.get_current_time())

    def notify_end(self, completed):
        self.change_listener.batch_end(completed)