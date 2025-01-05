import sys
import aqt.qt
import copy

from . import component_common 
from . import component_target
from . import component_voiceselection_easy
from . import config_models
from . import constants
from . import gui_utils
from . import logging_utils

logger = logging_utils.get_child_logger(__name__)

# The ComponentEasy component allows the user to generate audio for a single note. It's invoked from the Anki
# editor for a single note.

class ComponentEasy(component_common.ComponentBase):
    def __init__(self, hypertts, dialog, source_text, field_list):
        self.hypertts = hypertts
        self.dialog = dialog
        self.source_text = source_text

        self.batch_model = None

        # initialize sub-components
        self.target = component_target.BatchTarget(hypertts, field_list, self.model_update_target)
        self.voice_selection = component_voiceselection_easy.VoiceSelectionEasy(hypertts, dialog, self.model_update_voice_selection)
        self.batch_model = config_models.BatchConfig(self.hypertts.anki_utils)

    def draw(self, layout):
        # Create main vertical layout
        vlayout = aqt.qt.QVBoxLayout()

        # Add header with logo
        header_layout = aqt.qt.QHBoxLayout()
        header_layout.addStretch()
        header_layout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        vlayout.addLayout(header_layout)

        # Source text preview
        source_label = aqt.qt.QLabel('Source Text:')
        vlayout.addWidget(source_label)
        
        self.source_text_edit = aqt.qt.QPlainTextEdit()
        self.source_text_edit.setReadOnly(False)
        self.source_text_edit.setMinimumHeight(100)
        font = self.source_text_edit.font()
        font.setPointSize(20)  # increase font size
        self.source_text_edit.setFont(font)
        self.source_text_edit.setPlainText(self.source_text)
        vlayout.addWidget(self.source_text_edit)

        # Voice Selection group
        voice_group = aqt.qt.QGroupBox('Voice Selection')
        voice_layout = aqt.qt.QVBoxLayout()
        voice_layout.addWidget(self.voice_selection.draw())
        voice_group.setLayout(voice_layout)
        vlayout.addWidget(voice_group)

        # Target group
        target_group = aqt.qt.QGroupBox('Target Field')
        target_layout = aqt.qt.QHBoxLayout()
        target_layout.addWidget(self.target.draw())
        target_group.setLayout(target_layout)
        vlayout.addWidget(target_group)



        # Add buttons
        button_layout = aqt.qt.QHBoxLayout()
        self.preview_button = aqt.qt.QPushButton('Preview Audio')
        self.add_audio_button = aqt.qt.QPushButton('Add Audio')
        self.add_audio_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        self.cancel_button = aqt.qt.QPushButton('Cancel')
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.add_audio_button)
        button_layout.addWidget(self.cancel_button)
        vlayout.addLayout(button_layout)

        # Wire events
        self.preview_button.pressed.connect(self.preview_button_pressed)
        self.add_audio_button.pressed.connect(self.add_audio_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        layout.addLayout(vlayout)


    def model_update_target(self, model):
        self.batch_model.target = model

    def model_update_voice_selection(self, model):
        self.batch_model.voice_selection = model


    def sample_selected(self, note_id, text):
        self.source_text_edit.setPlainText(text)
        self.voice_selection.sample_text_selected(text)

    def batch_start(self):
        self.preview_button.setEnabled(False)
        self.add_audio_button.setEnabled(False)
        self.cancel_button.setText('Stop')

    def batch_end(self, completed):
        if completed:
            self.cancel_button.setText('Close')
        else:
            self.cancel_button.setText('Cancel')
            self.preview_button.setEnabled(True)
            self.add_audio_button.setEnabled(True)

    def preview_button_pressed(self):
        self.preview.preview_audio()

    def add_audio_button_pressed(self):
        self.preview.apply_audio_to_notes()

    def cancel_button_pressed(self):
        if self.cancel_button.text() == 'Stop':
            self.preview.batch_status.stop()
        else:
            self.dialog.close()

def create_component_easy(hypertts, source_text, field_list):
    dialog = aqt.qt.QDialog()
    easy_component = ComponentEasy(hypertts, dialog, source_text, field_list)
    layout = aqt.qt.QVBoxLayout()
    easy_component.draw(layout)
    dialog.setLayout(layout)
    dialog.show()
    return dialog
