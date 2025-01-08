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
    def __init__(self, hypertts, dialog, source_text, source_field, field_list):
        self.hypertts = hypertts
        self.dialog = dialog
        self.source_text = source_text
        self.original_width = None

        self.batch_model = None

        # initialize sub-components
        self.target = component_target_easy.BatchTargetEasy(hypertts, source_field, field_list, self.model_update_target)
        self.voice_selection = component_voiceselection_easy.VoiceSelectionEasy(hypertts, dialog, self.model_update_voice_selection)
        self.batch_model = config_models.BatchConfig(self.hypertts.anki_utils)

    def draw(self, layout):
        # Add header with logo at the top
        header_layout = aqt.qt.QHBoxLayout()
        header_layout.addStretch()
        header_layout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        layout.addLayout(header_layout)

        # Left side - vertical layout
        left_layout = aqt.qt.QVBoxLayout()

        # Source text preview
        source_label = gui_utils.get_medium_label('1. Source Text:')
        left_layout.addWidget(source_label)
        source_description_label = aqt.qt.QLabel(constants.GUI_TEXT_EASY_SOURCE_FIELD)
        left_layout.addWidget(source_description_label)
        
        self.source_text_edit = aqt.qt.QPlainTextEdit()
        self.source_text_edit.setReadOnly(False)
        self.source_text_edit.setMinimumHeight(50)
        font = self.source_text_edit.font()
        font.setPointSize(20)  # increase font size
        self.source_text_edit.setFont(font)
        self.source_text_edit.setPlainText(self.source_text)
        left_layout.addWidget(self.source_text_edit)

        # Voice Selection
        voice_label = gui_utils.get_medium_label('2. Voice Selection:')
        left_layout.addWidget(voice_label)
        voice_description_label = aqt.qt.QLabel(constants.GUI_TEXT_EASY_VOICE_SELECTION)
        left_layout.addWidget(voice_description_label)
        left_layout.addWidget(self.voice_selection.draw())
        left_layout.addStretch()

        # Right side - vertical layout in a widget container
        self.right_widget = aqt.qt.QWidget()
        right_layout = aqt.qt.QVBoxLayout(self.right_widget)

        # Target field
        target_label = gui_utils.get_medium_label('3. Target Field:')
        right_layout.addWidget(target_label)
        target_description_label = aqt.qt.QLabel(constants.GUI_TEXT_EASY_TARGET)
        right_layout.addWidget(target_description_label)
        right_layout.addWidget(self.target.draw())

        right_layout.addStretch()

        # Create main vertical layout for content
        main_content = aqt.qt.QVBoxLayout()
        
        # Create horizontal layout for left and right panes
        panes_layout = aqt.qt.QHBoxLayout()
        
        # Add left and right sides to panes layout
        panes_layout.addLayout(left_layout)
        panes_layout.addWidget(self.right_widget)
        self.right_widget.hide()  # hidden by default
        
        # Add panes to main content
        main_content.addLayout(panes_layout)
        
        # Add buttons at the bottom
        button_layout = aqt.qt.QHBoxLayout()
        button_layout.addStretch()  # Add spacer to push buttons to the right
        self.toggle_settings_button = aqt.qt.QPushButton(constants.GUI_TEXT_EASY_BUTTON_MORE_SETTINGS)
        self.preview_button = aqt.qt.QPushButton('Preview Audio')
        button_layout.addWidget(self.toggle_settings_button)
        self.add_audio_button = aqt.qt.QPushButton('Add Audio')
        self.add_audio_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        self.cancel_button = aqt.qt.QPushButton('Cancel')
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.add_audio_button)
        button_layout.addWidget(self.cancel_button)
        main_content.addLayout(button_layout)

        # Wire events
        self.preview_button.pressed.connect(self.preview_button_pressed)
        self.add_audio_button.pressed.connect(self.add_audio_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)
        self.toggle_settings_button.pressed.connect(self.toggle_settings)

        # Add everything to main layout
        layout.addLayout(main_content)


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

    def toggle_settings(self):
        if self.right_widget.isVisible():
            self.right_widget.hide()
            self.toggle_settings_button.setText(constants.GUI_TEXT_EASY_BUTTON_MORE_SETTINGS)
            # Restore original width if we have it stored
            if self.original_width is not None:
                self.dialog.resize(self.original_width, self.dialog.height())
        else:
            # Store current width before showing additional settings
            self.original_width = self.dialog.width()
            self.right_widget.show()
            self.toggle_settings_button.setText(constants.GUI_TEXT_EASY_BUTTON_HIDE_MORE_SETTINGS)

class EasyDialog(aqt.qt.QDialog):
    def __init__(self, hypertts):
        super(aqt.qt.QDialog, self).__init__()
        self.hypertts = hypertts
        self.setWindowTitle(constants.GUI_EASY_DIALOG_TITLE)
        self.main_layout = aqt.qt.QVBoxLayout(self)

    def configure(self, source_text: str, source_field, other_field_list):
        easy_component = ComponentEasy(self.hypertts, self, source_text, source_field, other_field_list)
        layout = aqt.qt.QVBoxLayout()
        easy_component.draw(self.main_layout)
        self.easy_component = easy_component

def create_component_easy(hypertts, source_text, source_field, field_list):
    dialog = EasyDialog(hypertts)
    # remove source_field from field_list
    other_field_list = copy.deepcopy(field_list)
    if source_field in field_list:
        other_field_list.remove(source_field)
    dialog.configure(source_text, source_field, field_list)
    hypertts.anki_utils.wait_for_dialog_input(dialog, constants.DIALOG_ID_EASY)
