import sys
import aqt.qt

from . import component_common
from . import component_batch
from . import config_models
from . import constants
from . import errors
from . import gui_utils
from . import logging_utils
logger = logging_utils.get_child_logger(__name__)


class ComponentMappingRule(component_common.ConfigComponentBase):

    def __init__(self, hypertts, editor_context: config_models.EditorContext, 
            model_change_callback, 
            model_delete_callback,
            request_started_callback,
            request_finished_callback):
        self.hypertts = hypertts
        self.model = None
        self.editor_context = editor_context
        self.model_change_callback = model_change_callback
        self.model_delete_callback = model_delete_callback
        self.request_started_callback = request_started_callback
        self.request_finished_callback = request_finished_callback

    def load_model(self, model):
        logger.info('load_model')
        self.model = model
        try:
            self.preset_name_label.setText(self.hypertts.get_preset_name(self.model.preset_id))
        except errors.PresetNotFound as e:
            self.preset_name_label.setText(constants.GUI_TEXT_UNKNOWN_PRESET)
        if self.model.rule_type == constants.MappingRuleType.NoteType:
            self.rule_type_note_type.setChecked(True)
        elif self.model.rule_type == constants.MappingRuleType.DeckNoteType:
            self.rule_type_deck_note_type.setChecked(True)

        self.enabled_checkbox.setChecked(self.model.enabled)
        logger.debug(f'enabled_checkbox.isChecked(): {self.enabled_checkbox.isChecked()}')


    def get_model(self):
        return self.model

    def draw(self, gridlayout, gridlayout_index):
        logger.debug('draw')

        self.preview_button = aqt.qt.QPushButton('Preview')
        self.preview_button.setToolTip('Hear audio for this preset')
        self.preview_button.setObjectName(f'preview_button_{gridlayout_index}')
        self.run_button = aqt.qt.QPushButton('Run')
        self.run_button.setToolTip('Add audio to the note for this preset')
        self.run_button.setObjectName(f'run_button_{gridlayout_index}')
        
        column_index = 0
        gridlayout.addWidget(self.preview_button, gridlayout_index, column_index)
        column_index += 1
        gridlayout.addWidget(self.run_button, gridlayout_index, column_index)
        column_index += 1

        preset_description_label = aqt.qt.QLabel('Preset:')
        gridlayout.addWidget(preset_description_label, gridlayout_index, column_index)
        column_index += 1

        self.preset_name_label = aqt.qt.QLabel()
        self.preset_name_label.setObjectName(f'preset_name_label_{gridlayout_index}')
        gridlayout.addWidget(self.preset_name_label, gridlayout_index, column_index)
        gridlayout.setColumnStretch(column_index, 1)
        column_index += 1

        self.edit_button = aqt.qt.QPushButton('Edit')
        self.edit_button.setToolTip('Edit this preset (to change voice or other settings)')
        self.edit_button.setObjectName(f'edit_button_{gridlayout_index}')
        gridlayout.addWidget(self.edit_button, gridlayout_index, column_index)
        column_index += 1        

        self.rule_type_group = aqt.qt.QButtonGroup()
        self.rule_type_note_type = aqt.qt.QRadioButton('Note Type')
        self.rule_type_deck_note_type = aqt.qt.QRadioButton('Deck and Note Type')
        self.rule_type_group.addButton(self.rule_type_note_type)
        self.rule_type_group.addButton(self.rule_type_deck_note_type)

        gridlayout.addWidget(self.rule_type_note_type, gridlayout_index, column_index)
        column_index += 1
        gridlayout.addWidget(self.rule_type_deck_note_type, gridlayout_index, column_index)
        column_index += 1
        # hlayout.addWidget(self.rule_type_group)

        self.enabled_checkbox = aqt.qt.QCheckBox(f'Enabled')
        self.enabled_checkbox.setObjectName(f'enabled_checkbox_{gridlayout_index}')
        gridlayout.addWidget(self.enabled_checkbox, gridlayout_index, column_index)
        column_index += 1

        self.delete_rule_button = aqt.qt.QPushButton('Delete')
        self.delete_rule_button.setObjectName(f'delete_rule_button_{gridlayout_index}')
        gridlayout.addWidget(self.delete_rule_button, gridlayout_index, column_index)
        column_index += 1

        # wire events
        self.preview_button.clicked.connect(self.preview_button_clicked)
        self.run_button.clicked.connect(self.run_button_clicked)
        self.rule_type_note_type.toggled.connect(self.rule_type_toggled)
        self.enabled_checkbox.toggled.connect(self.enabled_toggled)
        self.delete_rule_button.clicked.connect(self.delete_button_clicked)
        self.edit_button.clicked.connect(self.edit_button_clicked)

    def notify_model_update(self):
        self.model_change_callback(self.model)

    def rule_type_toggled(self, checked):
        logger.debug(f'rule_type_toggled: {checked}')
        if self.rule_type_note_type.isChecked():
            logger.debug(f'rule_type_note_type is checked')
            self.model.rule_type = constants.MappingRuleType.NoteType
        elif self.rule_type_deck_note_type.isChecked():
            logger.debug(f'rule_type_deck_note_type is checked')
            self.model.rule_type = constants.MappingRuleType.DeckNoteType
        else:
            raise RuntimeError(f'Unknown rule_type: {self.model.rule_type}')
        self.notify_model_update()

    def enabled_toggled(self, checked):
        logger.debug(f'enabled_toggled: {checked}')
        self.model.enabled = checked
        self.notify_model_update()

    def preview_button_clicked(self):
        logger.debug('preview_button_clicked')
        self.disable_preview_run()
        self.request_started_callback()
        self.hypertts.anki_utils.run_in_background(self.sound_preview_task, self.sound_preview_task_done)

    def edit_button_clicked(self):
        with self.hypertts.error_manager.get_single_action_context('Editing Preset'):
            component_batch.create_dialog_editor_existing_preset(self.hypertts, self.editor_context, self.model.preset_id)

    def delete_button_clicked(self):
        # self.hypertts.anki_utils.run_on_main(self.model_delete_callback)
        self.model_delete_callback()

    def disable_preview_run(self):
        """disable preview and run buttons, a preview or run is already in progress"""
        self.preview_button.setEnabled(False)
        self.run_button.setEnabled(False)
    
    def enable_preview_run(self):
        """done previewing/running, re-enable buttons"""
        self.preview_button.setEnabled(True)
        self.run_button.setEnabled(True)
        
    # preview functions
    # =================

    def sound_preview_task(self):
        if self.editor_context.note == None:
            raise errors.NoNotesSelectedPreview()
        preset = self.hypertts.load_preset(self.model.preset_id)
        self.hypertts.preview_note_audio_editor(preset, self.editor_context)
        return True

    def sound_preview_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Playing Sound Preview'):
            result = result.result()
        self.hypertts.anki_utils.run_on_main(self.finish_sound_preview)
    
    def finish_sound_preview(self):
        self.enable_preview_run()
        self.request_finished_callback()

    # add audio functions
    # ===================

    def run_button_clicked(self):
        logger.debug('run_button_clicked')
        self.disable_preview_run()
        self.request_started_callback()
        self.hypertts.anki_utils.run_in_background(self.apply_note_editor_task, self.apply_note_editor_task_done)

    def apply_note_editor_task(self):
        logger.debug('apply_note_editor_task')
        preset = self.hypertts.load_preset(self.model.preset_id)
        self.hypertts.editor_note_add_audio(preset, self.editor_context)
        return True

    def apply_note_editor_task_done(self, result):
        logger.debug('apply_note_editor_task_done')
        with self.hypertts.error_manager.get_single_action_context('Adding Audio to Note'):
            result = result.result()
        self.hypertts.anki_utils.run_on_main(self.finish_apply_note_editor)
    
    def finish_apply_note_editor(self):
        self.enable_preview_run()
        self.request_finished_callback()