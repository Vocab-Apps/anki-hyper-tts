import sys
import aqt.qt
import copy

from . import component_common 
from . import component_target_easy
from . import component_voiceselection_easy
from . import component_easy_source
from . import config_models
from . import constants
from . import gui_utils
from . import logging_utils
from . import errors

logger = logging_utils.get_child_logger(__name__)

# The ComponentEasy component allows the user to generate audio for a single note. It's invoked from the Anki
# editor for a single note.

# todo:
# add load_model logic for ComponentEasy, and test

class ComponentEasy(component_common.ComponentBase):
    BUTTON_TEXT_PREVIEW_AUDIO = 'Preview Audio'
    BUTTON_TEXT_PREVIEWING = 'Playing Preview...'
    BUTTON_TEXT_ADD_AUDIO = 'Add Audio'
    BUTTON_TEXT_ADDING_AUDIO = 'Adding Audio...'

    def __init__(self, hypertts, dialog, deck_note_type: config_models.DeckNoteType, editor_context: config_models.EditorContext):
        self.hypertts = hypertts
        self.dialog = dialog
        self.deck_note_type = deck_note_type
        self.editor_context = editor_context
        self.original_width = None
        self.batch_model = None

        # initialize source component
        self.source = component_easy_source.ComponentEasySource(hypertts, editor_context, self.model_update_source)
        source_field = editor_context.current_field
        field_list = field_list = list(editor_context.note.keys())
        # remove source field
        if source_field in field_list:
            field_list.remove(source_field)

        # initialize sub-components
        self.target = component_target_easy.BatchTargetEasy(hypertts, source_field, field_list, self.model_update_target)
        self.voice_selection = component_voiceselection_easy.VoiceSelectionEasy(hypertts, dialog, self.model_update_voice_selection)
        
        # configure the model
        self.batch_model = config_models.BatchConfig(self.hypertts.anki_utils)
        self.set_model_defaults()


    def set_model_defaults(self):
        # this will get overwritten if we load a model
        self.batch_model.name = self.hypertts.get_default_easy_preset_name(self.deck_note_type)
        # set dummy source, will not get used
        self.batch_model.source = config_models.BatchSource(
            mode=constants.BatchMode.simple,
            source_field=self.editor_context.current_field
        )
        # default text processing
        self.batch_model.text_processing = config_models.TextProcessing()

    def draw(self, layout):
        # Add header with logo at the top
        header_layout = aqt.qt.QHBoxLayout()
        header_layout.addStretch()
        header_layout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        layout.addLayout(header_layout)

        # Left side - vertical layout
        left_layout = aqt.qt.QVBoxLayout()

        # Add source component
        left_layout.addWidget(self.source.draw())

        # Voice Selection group
        voice_group = aqt.qt.QGroupBox('Voice Selection')
        voice_group_layout = aqt.qt.QVBoxLayout()
        voice_description_label = aqt.qt.QLabel(constants.GUI_TEXT_EASY_VOICE_SELECTION)
        voice_group_layout.addWidget(voice_description_label)
        voice_group_layout.addWidget(self.voice_selection.draw())
        voice_group.setLayout(voice_group_layout)
        left_layout.addWidget(voice_group)
        left_layout.addStretch()

        # Right side - vertical layout in a widget container
        self.right_widget = aqt.qt.QWidget()
        right_layout = aqt.qt.QVBoxLayout(self.right_widget)

        # Target field group
        target_group = aqt.qt.QGroupBox('Target Field')
        target_group_layout = aqt.qt.QVBoxLayout()
        target_description_label = aqt.qt.QLabel(constants.GUI_TEXT_EASY_TARGET)
        target_group_layout.addWidget(target_description_label)
        target_group_layout.addWidget(self.target.draw())
        target_group.setLayout(target_group_layout)
        right_layout.addWidget(target_group)

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
        self.preview_sound_button = aqt.qt.QPushButton(self.BUTTON_TEXT_PREVIEW_AUDIO)
        button_layout.addWidget(self.toggle_settings_button)
        self.add_audio_button = aqt.qt.QPushButton(self.BUTTON_TEXT_ADD_AUDIO)
        self.add_audio_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        self.cancel_button = aqt.qt.QPushButton('Cancel')
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        button_layout.addWidget(self.preview_sound_button)
        button_layout.addWidget(self.add_audio_button)
        button_layout.addWidget(self.cancel_button)
        main_content.addLayout(button_layout)

        # Wire events
        self.preview_sound_button.pressed.connect(self.preview_button_pressed)
        self.add_audio_button.pressed.connect(self.add_audio_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)
        self.toggle_settings_button.pressed.connect(self.toggle_settings)

        # Add everything to main layout
        layout.addLayout(main_content)


    def model_update_source(self, model):
        self.batch_model.source = model

    def model_update_target(self, model):
        self.batch_model.target = model

    def model_update_voice_selection(self, model):
        self.batch_model.voice_selection = model


    def sample_selected(self, note_id, text):
        self.source.source_text_edit.setPlainText(text)
        self.voice_selection.sample_text_selected(text)

    def batch_start(self):
        self.preview_sound_button.setEnabled(False)
        self.add_audio_button.setEnabled(False)
        self.cancel_button.setText('Stop')

    def batch_end(self, completed):
        if completed:
            self.cancel_button.setText('Close')
        else:
            self.cancel_button.setText('Cancel')
            self.preview_sound_button.setEnabled(True)
            self.add_audio_button.setEnabled(True)

    def get_source_text(self):
        return self.source.get_current_text()

    # preview audio handling
    # ======================

    def preview_button_pressed(self):
        self.preview_sound_button.setText(self.BUTTON_TEXT_PREVIEWING)
        self.hypertts.anki_utils.run_in_background(self.sound_preview_task, self.sound_preview_task_done)

    def sound_preview_task(self):
        # get text
        self.hypertts.preview_note_audio(self.batch_model, self.editor_context.note, self.get_source_text())
        return True

    def sound_preview_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Playing Sound Preview'):
            result = result.result()
        self.hypertts.anki_utils.run_on_main(self.finish_sound_preview)

    def finish_sound_preview(self):
        self.preview_sound_button.setText(self.BUTTON_TEXT_PREVIEW_AUDIO)

    # add audio handling
    # ==================

    def add_audio_button_pressed(self):
        self.add_audio_button.setText(self.BUTTON_TEXT_ADDING_AUDIO)
        self.add_audio_button.setEnabled(False)
        self.hypertts.anki_utils.run_in_background(self.add_audio_task, self.add_audio_task_done)

    def add_audio_task(self):
        logger.debug('add_audio_task')
        self.hypertts.editor_note_add_audio(self.batch_model, self.editor_context, text_input=self.get_source_text())
        return True

    def add_audio_task_done(self, result):
        logger.debug('add_audio_task_done')
        with self.hypertts.error_manager.get_single_action_context('Adding Audio to Note'):
            result = result.result()
            self.dialog.close()
        self.hypertts.anki_utils.run_on_main(self.finish_add_audio)
    
    def finish_add_audio(self):
        self.add_audio_button.setText(self.BUTTON_TEXT_ADD_AUDIO)
        self.add_audio_button.setEnabled(True)

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
                self.dialog.setFixedWidth(self.original_width)
                self.dialog.setMinimumWidth(0)
                self.dialog.setMaximumWidth(16777215)  # Qt's QWIDGETSIZE_MAX
        else:
            # Store current width before showing additional settings
            self.original_width = self.dialog.width()
            self.right_widget.show()
            self.toggle_settings_button.setText(constants.GUI_TEXT_EASY_BUTTON_HIDE_MORE_SETTINGS)
            # Let the dialog adjust to the new content
            self.dialog.adjustSize()

class EasyDialog(aqt.qt.QDialog):
    def __init__(self, hypertts):
        super(aqt.qt.QDialog, self).__init__()
        self.hypertts = hypertts
        self.setWindowTitle(constants.GUI_EASY_DIALOG_TITLE)
        self.main_layout = aqt.qt.QVBoxLayout(self)

    def configure(self, deck_note_type: config_models.DeckNoteType, editor_context: config_models.EditorContext):
        easy_component = ComponentEasy(self.hypertts, self, deck_note_type, editor_context)
        layout = aqt.qt.QVBoxLayout()
        easy_component.draw(self.main_layout)
        self.easy_component = easy_component
        # Set initial size
        self.adjustSize()

    def close(self):
        self.closed = True
        self.accept()


def create_dialog_editor(hypertts, deck_note_type: config_models.DeckNoteType, editor_context: config_models.EditorContext):
    dialog = EasyDialog(hypertts)
    dialog.configure(deck_note_type, editor_context)
    hypertts.anki_utils.wait_for_dialog_input(dialog, constants.DIALOG_ID_EASY)
