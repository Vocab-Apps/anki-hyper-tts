import sys
import aqt.qt

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)


class ComponentMappingRule(component_common.ConfigComponentBase):

    def __init__(self, hypertts, editor, note, add_mode: bool, model_change_callback):
        self.hypertts = hypertts
        self.model = None
        self.editor = editor
        self.note = note
        self.add_mode = add_mode
        self.model_change_callback = model_change_callback

    def load_model(self, model):
        logger.info('load_model')
        self.model = model
        self.preset_name_label.setText(self.hypertts.get_preset_name(self.model.preset_id))
        if self.model.rule_type == constants.MappingRuleType.NoteType:
            self.rule_type_note_type.setChecked(True)
        elif self.model.rule_type == constants.MappingRuleType.DeckNoteType:
            self.rule_type_deck_note_type.setChecked(True)

        self.enabled_checkbox.setChecked(self.model.enabled)

    def get_model(self):
        return self.model

    def draw(self, gridlayout, gridlayout_index):
        # todo: needs to draw itself into a gridlayout

        self.preview_button = aqt.qt.QPushButton('Preview')
        self.run_button = aqt.qt.QPushButton('Run')
        
        column_index = 0
        gridlayout.addWidget(self.preview_button, gridlayout_index, column_index)
        gridlayout.addWidget(self.run_button, gridlayout_index, column_index + 1)

        preset_description_label = aqt.qt.QLabel('Preset:')
        gridlayout.addWidget(preset_description_label)

        self.preset_name_label = aqt.qt.QLabel()
        gridlayout.addWidget(self.preset_name_label, gridlayout_index, column_index + 2)

        self.rule_type_group = aqt.qt.QButtonGroup()
        self.rule_type_note_type = aqt.qt.QRadioButton('Note Type')
        self.rule_type_deck_note_type = aqt.qt.QRadioButton('Deck and Note Type')
        self.rule_type_group.addButton(self.rule_type_note_type)
        self.rule_type_group.addButton(self.rule_type_deck_note_type)

        gridlayout.addWidget(self.rule_type_note_type, gridlayout_index, column_index + 3)
        gridlayout.addWidget(self.rule_type_deck_note_type, gridlayout_index, column_index + 4)
        # hlayout.addWidget(self.rule_type_group)

        self.enabled_checkbox = aqt.qt.QCheckBox(f'Enabled')
        gridlayout.addWidget(self.enabled_checkbox, gridlayout_index, column_index + 5)

        # wire events
        self.preview_button.clicked.connect(self.preview_button_clicked)
        self.run_button.clicked.connect(self.run_button_clicked)
        self.rule_type_note_type.toggled.connect(self.rule_type_toggled)
        self.enabled_checkbox.toggled.connect(self.enabled_toggled)

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
        self.preview_button.setText('Playing...')
        self.hypertts.anki_utils.run_in_background(self.sound_preview_task, self.sound_preview_task_done)

    # preview functions
    # =================

    def sound_preview_task(self):
        if self.note == None:
            raise errors.NoNotesSelectedPreview()
        preset = self.hypertts.load_preset(self.model.preset_id)
        self.hypertts.preview_note_audio(preset, self.note, None)
        return True

    def sound_preview_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Playing Sound Preview'):
            result = result.result()
        self.hypertts.anki_utils.run_on_main(self.finish_sound_preview)
    
    def finish_sound_preview(self):
        self.preview_button.setText('Preview')

    # add audio functions
    # ===================

    def run_button_clicked(self):
        self.run_button.setText('Running...')
        self.hypertts.anki_utils.run_in_background(self.apply_note_editor_task, self.apply_note_editor_task_done)

    def apply_note_editor_task(self):
        logger.debug('apply_note_editor_task')
        preset = self.hypertts.load_preset(self.model.preset_id)
        self.hypertts.editor_note_add_audio(preset, self.editor, self.note, self.add_mode, None)
        return True

    def apply_note_editor_task_done(self, result):
        logger.debug('apply_note_editor_task_done')
        with self.hypertts.error_manager.get_single_action_context('Adding Audio to Note'):
            result = result.result()
        self.hypertts.anki_utils.run_on_main(self.finish_apply_note_editor)
    
    def finish_apply_note_editor(self):
        self.run_button.setText('Run')