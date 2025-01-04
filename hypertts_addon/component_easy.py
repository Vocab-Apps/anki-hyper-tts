import sys
import aqt.qt
import copy

from . import component_common 
from . import component_target
from . import component_voiceselection
from . import component_text_processing
from . import component_easy_preview
from . import config_models
from . import constants
from . import gui_utils
from . import logging_utils

logger = logging_utils.get_child_logger(__name__)

# The ComponentEasy component allows the user to generate audio for a single note. It's invoked from the Anki
# editor for a single note.

class ComponentEasy(component_common.ComponentBase):
    def __init__(self, hypertts, dialog, note_id_list, profile_name):
        self.hypertts = hypertts
        self.dialog = dialog
        self.note_id_list = note_id_list
        self.profile_name = profile_name

        self.batch_model = None

        # initialize sub-components
        field_list = hypertts.get_all_fields_from_notes(note_id_list)
        self.target = component_target.BatchTarget(hypertts, field_list, self.model_update_target)
        self.voice_selection = component_voiceselection.VoiceSelection(hypertts, dialog, self.model_update_voice_selection)
        self.text_processing = component_text_processing.TextProcessing(hypertts, self.model_update_text_processing)
        self.preview = component_easy_preview.EasyPreview(hypertts, dialog, note_id_list,
            self.sample_selected, self.batch_start, self.batch_end)

        self.batch_model = config_models.BatchConfig(self.hypertts.anki_utils)
        self.batch_model.name = profile_name

    def draw(self, layout):
        # Create main vertical layout
        vlayout = aqt.qt.QVBoxLayout()

        # Source text preview
        self.source_text = aqt.qt.QPlainTextEdit()
        self.source_text.setReadOnly(False)
        self.source_text.setMinimumHeight(100)
        vlayout.addWidget(self.source_text)

        # Target group
        target_group = aqt.qt.QGroupBox('Target Field')
        target_layout = aqt.qt.QHBoxLayout()
        target_layout.addWidget(self.target.draw())
        target_group.setLayout(target_layout)
        vlayout.addWidget(target_group)

        # Voice Selection group
        voice_group = aqt.qt.QGroupBox('Voice Selection')
        voice_layout = aqt.qt.QVBoxLayout()
        voice_layout.addWidget(self.voice_selection.draw())
        voice_group.setLayout(voice_layout)
        vlayout.addWidget(voice_group)

        # Text Processing group
        text_group = aqt.qt.QGroupBox('Text Processing')
        text_layout = aqt.qt.QVBoxLayout()
        text_layout.addWidget(self.text_processing.draw())
        text_group.setLayout(text_layout)
        vlayout.addWidget(text_group)

        # Preview group
        preview_group = aqt.qt.QGroupBox('Preview')
        preview_layout = aqt.qt.QVBoxLayout()
        preview_layout.addLayout(self.preview.draw())
        preview_group.setLayout(preview_layout)
        vlayout.addWidget(preview_group)

        # Add buttons
        button_layout = aqt.qt.QHBoxLayout()
        self.apply_button = aqt.qt.QPushButton('Apply to Notes')
        self.cancel_button = aqt.qt.QPushButton('Cancel')
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        vlayout.addLayout(button_layout)

        # Wire events
        self.apply_button.pressed.connect(self.apply_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        layout.addLayout(vlayout)


    def model_update_target(self, model):
        self.batch_model.target = model
        self.preview.load_model(self.batch_model)

    def model_update_voice_selection(self, model):
        self.batch_model.voice_selection = model
        self.preview.load_model(self.batch_model)

    def model_update_text_processing(self, model):
        self.batch_model.text_processing = model
        self.preview.load_model(self.batch_model)

    def sample_selected(self, note_id, text):
        self.source_text.setPlainText(text)
        self.voice_selection.sample_text_selected(text)

    def batch_start(self):
        self.apply_button.setEnabled(False)
        self.cancel_button.setText('Stop')

    def batch_end(self, completed):
        if completed:
            self.cancel_button.setText('Close')
        else:
            self.cancel_button.setText('Cancel')
            self.apply_button.setEnabled(True)

    def apply_button_pressed(self):
        self.preview.apply_audio_to_notes()

    def cancel_button_pressed(self):
        if self.cancel_button.text() == 'Stop':
            self.preview.batch_status.stop()
        else:
            self.dialog.close()

def create_component_easy(hypertts, note_id_list, profile_name):
    dialog = aqt.qt.QDialog()
    easy_component = ComponentEasy(hypertts, dialog, note_id_list, profile_name)
    layout = aqt.qt.QVBoxLayout()
    easy_component.draw(layout)
    dialog.setLayout(layout)
    dialog.show()
    return dialog
