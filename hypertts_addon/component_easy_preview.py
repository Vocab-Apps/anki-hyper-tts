import aqt.qt
from . import component_common
from . import logging_utils

logger = logging_utils.get_child_logger(__name__)

class EasyPreview(component_common.ComponentBase):
    def __init__(self, hypertts, dialog, source_text, sample_callback, batch_start_callback, batch_end_callback):
        self.hypertts = hypertts
        self.dialog = dialog
        self.source_text = source_text
        self.sample_callback = sample_callback
        self.batch_start_callback = batch_start_callback
        self.batch_end_callback = batch_end_callback
        self.batch_model = None

    def draw(self):
        layout = aqt.qt.QVBoxLayout()
        self.sample_callback(self.source_text)
        return layout

    def populate_note_selector(self):
        self.note_selector.clear()
        for note_id in self.note_id_list:
            note = self.hypertts.anki_utils.get_note_by_id(note_id)
            self.note_selector.addItem(f'Note {note_id}', note_id)

    def load_model(self, model):
        self.batch_model = model

    def apply_audio_to_notes(self):
        self.batch_start_callback()
        try:
            self.hypertts.process_batch(self.batch_model, self.note_id_list)
            self.batch_end_callback(True)
        except Exception as e:
            logger.error(f'Error processing batch: {e}')
            self.batch_end_callback(False)
