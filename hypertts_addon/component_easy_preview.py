import aqt.qt
from . import component_common
from . import logging_utils

logger = logging_utils.get_child_logger(__name__)

class EasyPreview(component_common.ComponentBase):
    def __init__(self, hypertts, dialog, note_id_list, sample_callback, batch_start_callback, batch_end_callback):
        self.hypertts = hypertts
        self.dialog = dialog
        self.note_id_list = note_id_list
        self.sample_callback = sample_callback
        self.batch_start_callback = batch_start_callback
        self.batch_end_callback = batch_end_callback
        self.batch_model = None
        self.current_note = None

    def draw(self):
        layout = aqt.qt.QVBoxLayout()
        
        # Note selection
        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addWidget(aqt.qt.QLabel('Preview Note:'))
        self.note_selector = aqt.qt.QComboBox()
        self.populate_note_selector()
        self.note_selector.currentIndexChanged.connect(self.note_selected)
        hlayout.addWidget(self.note_selector)
        hlayout.addStretch()
        layout.addLayout(hlayout)

        return layout

    def populate_note_selector(self):
        self.note_selector.clear()
        for note_id in self.note_id_list:
            note = self.hypertts.anki_utils.get_note_by_id(note_id)
            self.note_selector.addItem(f'Note {note_id}', note_id)

    def note_selected(self, index):
        if index >= 0:
            note_id = self.note_id_list[index]
            note = self.hypertts.anki_utils.get_note_by_id(note_id)
            self.current_note = note
            
            if self.batch_model and self.batch_model.source:
                try:
                    source_text = self.hypertts.get_source_text(note, self.batch_model.source)
                    self.sample_callback(note_id, source_text)
                except Exception as e:
                    logger.warning(f'Could not get source text: {e}')

    def load_model(self, model):
        self.batch_model = model
        if self.current_note:
            self.note_selected(self.note_selector.currentIndex())

    def apply_audio_to_notes(self):
        self.batch_start_callback()
        try:
            self.hypertts.process_batch(self.batch_model, self.note_id_list)
            self.batch_end_callback(True)
        except Exception as e:
            logger.error(f'Error processing batch: {e}')
            self.batch_end_callback(False)
