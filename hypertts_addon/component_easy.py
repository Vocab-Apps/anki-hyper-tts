import sys
import aqt.qt
import copy

from . import component_common 
from . import component_target_easy
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
        self.target = component_target_easy.BatchTargetEasy(hypertts, field_list, self.model_update_target)
        self.voice_selection = component_voiceselection_easy.VoiceSelectionEasy(hypertts, dialog, self.model_update_voice_selection)
        self.batch_model = config_models.BatchConfig(self.hypertts.anki_utils)

    def draw(self, layout):
        # Create main horizontal layout
        hlayout = aqt.qt.QHBoxLayout()

        # Add header with logo at the top
        header_layout = aqt.qt.QHBoxLayout()
        header_layout.addStretch()
        header_layout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        layout.addLayout(header_layout)

        # Left side - vertical layout
        left_layout = aqt.qt.QVBoxLayout()

        # Source text preview
        source_label = aqt.qt.QLabel('Source Text:')
        left_layout.addWidget(source_label)
        
        self.source_text_edit = aqt.qt.QPlainTextEdit()
        self.source_text_edit.setReadOnly(False)
        self.source_text_edit.setMinimumHeight(50)
        font = self.source_text_edit.font()
        font.setPointSize(20)  # increase font size
        self.source_text_edit.setFont(font)
        self.source_text_edit.setPlainText(self.source_text)
        left_layout.addWidget(self.source_text_edit)

        # Voice Selection
        voice_label = aqt.qt.QLabel('Voice Selection:')
        left_layout.addWidget(voice_label)
        left_layout.addWidget(self.voice_selection.draw())
        left_layout.addStretch()

        # Add left side to main layout
        hlayout.addLayout(left_layout)

        # Add vertical separator
        separator = aqt.qt.QFrame()
        separator.setFrameShape(aqt.qt.QFrame.Shape.VLine)
        separator.setFrameShadow(aqt.qt.QFrame.Shadow.Sunken)
        hlayout.addWidget(separator)

        # Right side - vertical layout
        right_layout = aqt.qt.QVBoxLayout()

        # Target group
        target_group = aqt.qt.QGroupBox('Target Field:')
        target_layout = aqt.qt.QHBoxLayout()
        target_layout.addWidget(self.target.draw())
        target_group.setLayout(target_layout)
        right_layout.addWidget(target_group)

        right_layout.addStretch()

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
        right_layout.addLayout(button_layout)

        # Add right side to main layout
        hlayout.addLayout(right_layout)

        # Wire events
        self.preview_button.pressed.connect(self.preview_button_pressed)
        self.add_audio_button.pressed.connect(self.add_audio_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        layout.addLayout(hlayout)


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

class EasyDialog(aqt.qt.QDialog):
    def __init__(self, hypertts):
        super(aqt.qt.QDialog, self).__init__()
        self.hypertts = hypertts
        self.setWindowTitle(constants.GUI_EASY_DIALOG_TITLE)
        self.main_layout = aqt.qt.QVBoxLayout(self)

    def configure(self, source_text: str, field_list):
        easy_component = ComponentEasy(self.hypertts, self, source_text, field_list)
        layout = aqt.qt.QVBoxLayout()
        easy_component.draw(self.main_layout)
        self.easy_component = easy_component

def create_component_easy(hypertts, source_text, field_list):
    dialog = EasyDialog(hypertts)
    dialog.configure(source_text, field_list)
    hypertts.anki_utils.wait_for_dialog_input(dialog, constants.DIALOG_ID_EASY)
