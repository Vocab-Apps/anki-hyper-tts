import sys
import aqt.qt

from typing import List, Optional

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
component_source = __import__('component_source', globals(), locals(), [], sys._addon_import_level_base)
component_target = __import__('component_target', globals(), locals(), [], sys._addon_import_level_base)
component_voiceselection = __import__('component_voiceselection', globals(), locals(), [], sys._addon_import_level_base)
component_text_processing = __import__('component_text_processing', globals(), locals(), [], sys._addon_import_level_base)
component_batch_preview = __import__('component_batch_preview', globals(), locals(), [], sys._addon_import_level_base)
component_label_preview = __import__('component_label_preview', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)



class ComponentBatch(component_common.ConfigComponentBase):
    MIN_WIDTH_COMPONENT = 600
    MIN_HEIGHT = 250

    def __init__(self, hypertts, dialog):
        self.hypertts = hypertts
        self.dialog = dialog
        self.batch_model = config_models.BatchConfig(self.hypertts.anki_utils)
        self.model_changed = False
        self.note = None
        self.last_saved_preset_id = None
        self.editor_new_preset_id = None

        # create certain widgets upfront
        self.profile_name_label = aqt.qt.QLabel()
        self.show_settings_button = aqt.qt.QPushButton('Hide Settings')
        self.preview_sound_button = aqt.qt.QPushButton('Preview Sound')
        self.apply_button = aqt.qt.QPushButton('Apply to Notes')
        self.cancel_button = aqt.qt.QPushButton('Cancel')
        self.profile_open_button = aqt.qt.QPushButton('Open')
        self.profile_open_button.setToolTip('Open a different preset')
        self.profile_duplicate_button = aqt.qt.QPushButton('Duplicate')
        self.profile_duplicate_button.setToolTip('Duplicate an existing preset')
        self.profile_save_button = aqt.qt.QPushButton('Save')
        self.profile_save_button.setToolTip('Save current preset')
        self.profile_rename_button = aqt.qt.QPushButton('Rename')
        self.profile_rename_button.setToolTip('Rename the current preset')
        self.profile_delete_button = aqt.qt.QPushButton('Delete')
        self.profile_delete_button.setToolTip('Delete the current preset')
        self.profile_save_and_close_button = aqt.qt.QPushButton('Save and Close')
        self.profile_save_and_close_button.setToolTip('Save current preset and close dialog')

    def configure_browser(self, note_id_list):
        self.note_id_list = note_id_list
        field_list = self.hypertts.get_all_fields_from_notes(note_id_list)
        if len(field_list) == 0:
            raise Exception(f'could not find any fields in the selected {len(note_id_list)} notes')
        self.source = component_source.BatchSource(self.hypertts, field_list, self.source_model_updated)
        self.target = component_target.BatchTarget(self.hypertts, field_list, self.target_model_updated)
        self.voice_selection = component_voiceselection.VoiceSelection(self.hypertts, self.dialog, self.voice_selection_model_updated)
        self.text_processing = component_text_processing.TextProcessing(self.hypertts, self.text_processing_model_updated)
        self.preview = component_batch_preview.BatchPreview(self.hypertts, self.dialog, self.note_id_list, 
            self.sample_selected, self.apply_notes_batch_start, self.apply_notes_batch_end)
        self.editor_mode = False
        self.show_settings = True

    def configure_editor(self, editor_context: config_models.EditorContext):
        self.editor_context = editor_context
        self.note = editor_context.note
        self.editor = editor_context.editor
        self.add_mode = editor_context.add_mode
        field_list = list(self.note.keys())
        self.source = component_source.BatchSource(self.hypertts, field_list, self.source_model_updated)
        self.target = component_target.BatchTarget(self.hypertts, field_list, self.target_model_updated)
        self.voice_selection = component_voiceselection.VoiceSelection(self.hypertts, self.dialog, self.voice_selection_model_updated)
        self.text_processing = component_text_processing.TextProcessing(self.hypertts, self.text_processing_model_updated)
        self.preview = component_label_preview.LabelPreview(self.hypertts, self.note)
        self.editor_mode = True

    def new_preset(self, preset_name = None):
        """start with a new preset"""
        if preset_name == None:
            new_preset_name = self.hypertts.get_next_preset_name()
        else:
            new_preset_name = preset_name
        self.batch_model = config_models.BatchConfig(self.hypertts.anki_utils)
        self.batch_model.name = new_preset_name
        self.profile_name_label.setText(new_preset_name)
        self.model_changed = True
        self.update_save_profile_button_state()
        self.disable_delete_profile_button()

    def new_preset_after_delete(self):
        """new preset after user deleted the existing one"""
        # note: don't create new model, just reset the uuid, otherwise members of BatchConfig won't be initialized
        new_preset_name = self.hypertts.get_next_preset_name()
        self.batch_model.reset_uuid(self.hypertts.anki_utils)
        self.batch_model.name = new_preset_name
        self.profile_name_label.setText(new_preset_name)
        self.model_changed = True
        self.update_save_profile_button_state()
        self.disable_delete_profile_button()

    def load_preset(self, preset_id):
        model = self.hypertts.load_preset(preset_id)
        self.load_model(model)
        self.enable_delete_profile_button()

    def load_model(self, model):
        logger.info('load_model')
        self.batch_model = model
        # disseminate to all components
        self.profile_name_label.setText(model.name)
        self.source.load_model(model.source)
        self.target.load_model(model.target)
        self.voice_selection.load_model(model.voice_selection)
        self.text_processing.load_model(model.text_processing)
        self.preview.load_model(self.batch_model)

        self.model_changed = False
        self.update_save_profile_button_state()

    def get_model(self):
        return self.batch_model

    def source_model_updated(self, model):
        logger.info(f'source_model_updated: {model}')
        self.batch_model.set_source(model)
        self.model_part_updated_common()

    def target_model_updated(self, model):
        logger.info('target_model_updated')
        self.batch_model.set_target(model)
        self.model_part_updated_common()

    def voice_selection_model_updated(self, model):
        logger.info('voice_selection_model_updated')
        self.batch_model.set_voice_selection(model)
        self.model_part_updated_common()

    def text_processing_model_updated(self, model):
        logger.info('text_processing_model_updated')
        self.batch_model.text_processing = model
        self.model_part_updated_common()

    def model_part_updated_common(self):
        self.preview.load_model(self.batch_model)
        self.model_changed = True
        # are we in editor mode ? if so, set the sample text on the voice component
        if self.note != None:
            if self.batch_model.source != None and self.batch_model.text_processing != None:
                try:
                    source_text, processed_text = self.hypertts.get_source_processed_text(self.note, self.batch_model.source, self.batch_model.text_processing)
                    self.voice_selection.sample_text_selected(processed_text)
                except Exception as e:
                    logger.warning(f'could not set sample text: {e}')
        self.update_save_profile_button_state()

    def update_save_profile_button_state(self):
        if self.model_changed:
            self.enable_save_profile_button()
        else:
            self.disable_save_profile_button()

    def enable_save_profile_button(self):
        logger.info('enable_save_profile_button')
        self.profile_save_button.setEnabled(True)
        if self.editor_mode == False:
            self.profile_save_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())

    def disable_save_profile_button(self):
        logger.info('disable_save_profile_button')
        self.profile_save_button.setEnabled(False)
        self.profile_save_button.setStyleSheet(None)

    def enable_delete_profile_button(self):
        self.profile_delete_button.setEnabled(True)

    def disable_delete_profile_button(self):
        self.profile_delete_button.setEnabled(False)

    def sample_selected(self, note_id, text):
        self.voice_selection.sample_text_selected(text)
        self.note = self.hypertts.anki_utils.get_note_by_id(note_id)
        self.preview_sound_button.setEnabled(True)
        self.preview_sound_button.setText('Preview Sound')

    def draw(self, layout):
        self.vlayout = aqt.qt.QVBoxLayout()

        # profile management
        # ==================

        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addWidget(aqt.qt.QLabel('Preset:'))

        font = aqt.qt.QFont()
        font.setBold(True)
        self.profile_name_label.setFont(font)

        hlayout.addWidget(self.profile_name_label)
        hlayout.addWidget(self.profile_save_button)
        hlayout.addWidget(self.profile_rename_button)
        hlayout.addWidget(self.profile_delete_button)
        hlayout.addWidget(self.profile_open_button)
        hlayout.addWidget(self.profile_duplicate_button)


        hlayout.addStretch()
        # logo header
        hlayout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        self.vlayout.addLayout(hlayout)

        self.profile_open_button.pressed.connect(self.open_profile_button_pressed)
        self.profile_save_button.pressed.connect(self.save_profile_button_pressed)
        self.profile_delete_button.pressed.connect(self.delete_profile_button_pressed)
        self.profile_rename_button.pressed.connect(self.rename_profile_button_pressed)
        self.profile_duplicate_button.pressed.connect(self.duplicate_profile_button_pressed)

        # preset settings tabs
        # ====================

        self.tabs = aqt.qt.QTabWidget()

        self.tabs.addTab(self.source.draw(), 'Source')
        self.tabs.addTab(self.target.draw(), 'Target')
        self.tabs.addTab(self.voice_selection.draw(), 'Voice Selection')
        self.tabs.addTab(self.text_processing.draw(), 'Text Processing')

        if self.editor_mode == False:
            self.splitter = aqt.qt.QSplitter(aqt.qt.Qt.Orientation.Horizontal)
            self.splitter.addWidget(self.tabs)

            self.preview_widget = aqt.qt.QWidget()
            self.preview_widget.setLayout(self.preview.draw())
            self.splitter.addWidget(self.preview_widget)
            self.vlayout.addWidget(self.splitter, 1) # splitter is what should stretch
        else:
            self.vlayout.addWidget(self.tabs, 1) # the tabs should stretch
            self.preview_widget = aqt.qt.QWidget()
            self.preview_widget.setLayout(self.preview.draw())            
            self.vlayout.addWidget(self.preview_widget)


        # setup bottom buttons
        # ====================

        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addStretch()

        # show settings button
        if not self.editor_mode:
            hlayout.addWidget(self.show_settings_button)
        # preview button
        if not self.editor_mode:
            self.preview_sound_button.setText('Select Note to Preview Sound')
            self.preview_sound_button.setEnabled(False)
        hlayout.addWidget(self.preview_sound_button)
        # apply button
        apply_label_text = 'Apply To Notes'
        if self.editor_mode:
            apply_label_text = 'Apply To Note'
        self.apply_button.setText(apply_label_text)
        if self.editor_mode == False:
            self.apply_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        hlayout.addWidget(self.apply_button)
        # save and close
        if self.editor_mode == True:
            hlayout.addWidget(self.profile_save_and_close_button)
            self.profile_save_and_close_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        # cancel button
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        hlayout.addWidget(self.cancel_button)
        self.vlayout.addLayout(hlayout)

        self.show_settings_button.pressed.connect(self.show_settings_button_pressed)
        self.preview_sound_button.pressed.connect(self.sound_preview_button_pressed)
        self.apply_button.pressed.connect(self.apply_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)
        self.profile_save_and_close_button.pressed.connect(self.profile_save_and_close_button_pressed)

        self.cancel_button.setFocus()

        layout.addLayout(self.vlayout)

    def get_min_size(self):
        return self.MIN_HEIGHT

    def no_settings_editor(self):
        # when launched from the editor
        self.dialog.setMinimumSize(self.MIN_WIDTH_COMPONENT, self.get_min_size())

    def collapse_settings(self):
        # when we have already loaded a batch
        self.splitter.setSizes([0, self.MIN_WIDTH_COMPONENT])
        self.dialog.setMinimumSize(self.MIN_WIDTH_COMPONENT, self.get_min_size())
        self.show_settings = False
        self.show_settings_button.setText('Show Settings')

    def display_settings(self):
        # when configuring a new batch
        self.splitter.setSizes([self.MIN_WIDTH_COMPONENT, self.MIN_WIDTH_COMPONENT])
        self.dialog.setMinimumSize(self.MIN_WIDTH_COMPONENT * 2, self.get_min_size())
        self.show_settings = True
        self.show_settings_button.setText('Hide Settings')

    def choose_existing_preset(self, title):
        # returns preset_id if user chose a preset, None otherwise
        preset_list = self.hypertts.get_preset_list()
        preset_name_list = [preset.name for preset in preset_list]
        chosen_preset_row, retvalue = self.hypertts.anki_utils.ask_user_choose_from_list(self.dialog, title, preset_name_list)
        logger.info(f'chosen preset row: {chosen_preset_row}, retvalue: {retvalue}')
        if retvalue == 1:
            preset_id = preset_list[chosen_preset_row].id
            return preset_id
        return None

    def open_profile_button_pressed(self):
        with self.hypertts.error_manager.get_single_action_context('Opening Profile'):
            preset_id = self.choose_existing_preset('Choose a preset to open')
            if preset_id != None:
                self.load_preset(preset_id)

    def duplicate_profile_button_pressed(self):
        with self.hypertts.error_manager.get_single_action_context('Duplicating Profile'):
            preset_id = self.choose_existing_preset('Choose a preset to duplicate')
            if preset_id != None:
                # load preset, and change uuid
                self.load_preset(preset_id)
                self.batch_model.reset_uuid(self.hypertts.anki_utils)
                # rename the preset
                new_profile_name = self.batch_model.name + ' (copy)'
                self.batch_model.name = new_profile_name
                # reflect new name
                self.profile_name_label.setText(new_profile_name)
                # indicate the model has changed
                self.model_changed = True
                self.update_save_profile_button_state()


    def save_profile(self):
        with self.hypertts.error_manager.get_single_action_context('Saving Preset'):
            self.hypertts.save_preset(self.get_model())
            self.model_changed = False
            self.last_saved_preset_id = self.get_model().uuid
            self.update_save_profile_button_state()
            self.enable_delete_profile_button()

    def save_profile_if_changed(self):
        if self.model_changed:
            # does the user want to save the profile ?
            proceed = self.hypertts.anki_utils.ask_user('Save changes to current preset ?', self.dialog)
            if proceed:
                self.save_profile()

    def save_profile_button_pressed(self):
        self.save_profile()

    def rename_profile_button_pressed(self):
        current_profile_name = self.batch_model.name
        new_profile_name, result = self.hypertts.anki_utils.ask_user_get_text(
            'Enter new preset name', self.dialog, current_profile_name, 'Rename Preset')
        if result == 1:
            # user pressed ok, rename profile
            self.batch_model.name = new_profile_name
            # reflect new name
            self.profile_name_label.setText(new_profile_name)
            # enable save button
            self.model_changed = True
            self.update_save_profile_button_state()

    def delete_profile_button_pressed(self):
        profile_name = self.batch_model.name
        preset_id = self.batch_model.uuid
        proceed = self.hypertts.anki_utils.ask_user(f'Delete Preset {profile_name} ?', self.dialog)
        if proceed == True:
            with self.hypertts.error_manager.get_single_action_context('Deleting Preset'):
                self.hypertts.delete_preset(preset_id)
                self.new_preset_after_delete()

    def show_settings_button_pressed(self):
        if self.show_settings:
            self.collapse_settings()
        else:
            self.display_settings()

    def sound_preview_button_pressed(self):
        self.disable_bottom_buttons()
        self.preview_sound_button.setText('Playing Preview...')
        self.hypertts.anki_utils.run_in_background(self.sound_preview_task, self.sound_preview_task_done)

    def profile_save_and_close_button_pressed(self):
        self.save_profile()
        self.editor_new_preset_id = self.last_saved_preset_id
        self.dialog.close()

    def apply_button_pressed(self):
        with self.hypertts.error_manager.get_single_action_context('Applying Audio to Notes'):
            self.get_model().validate()
            logger.info('apply_button_pressed')
            if self.editor_mode:
                self.disable_bottom_buttons()
                self.apply_button.setText('Loading...')
                self.hypertts.anki_utils.run_in_background(self.apply_note_editor_task, self.apply_note_editor_task_done)
            else:
                self.disable_bottom_buttons()
                self.apply_button.setText('Loading...')
                self.preview.apply_audio_to_notes()

    def cancel_button_pressed(self):
        self.dialog.close()

    def apply_note_editor_task(self):
        logger.debug('apply_note_editor_task')
        self.hypertts.editor_note_add_audio(self.batch_model, self.editor_context)
        return True

    def apply_note_editor_task_done(self, result):
        logger.debug('apply_note_editor_task_done')
        with self.hypertts.error_manager.get_single_action_context('Adding Audio to Note'):
            result = result.result()
            self.dialog.close()
        self.hypertts.anki_utils.run_on_main(self.finish_apply_note_editor)
    
    def finish_apply_note_editor(self):
        self.enable_bottom_buttons()
        self.apply_button.setText('Apply To Note')

    def sound_preview_task(self):
        if self.note == None:
            raise errors.NoNotesSelectedPreview()
        self.hypertts.preview_note_audio(self.batch_model, self.note, None)
        return True

    def sound_preview_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Playing Sound Preview'):
            result = result.result()
        self.hypertts.anki_utils.run_on_main(self.finish_sound_preview)

    def finish_sound_preview(self):
        self.enable_bottom_buttons()
        self.preview_sound_button.setText('Preview Sound')

    def disable_bottom_buttons(self):
        self.preview_sound_button.setEnabled(False)
        self.apply_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

    def enable_bottom_buttons(self):
        self.preview_sound_button.setEnabled(True)
        self.apply_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

    def apply_notes_batch_start(self):
        pass

    def batch_interrupted_button_setup(self):
        self.enable_bottom_buttons()
        self.apply_button.setText('Apply To Notes')

    def batch_completed_button_setup(self):
        self.cancel_button.setText('Close')
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        self.cancel_button.setEnabled(True)
        self.apply_button.setStyleSheet(None)
        self.apply_button.setText('Done')

    def apply_notes_batch_end(self, completed):
        if completed:
            self.hypertts.anki_utils.run_on_main(self.batch_completed_button_setup)
        else:
            self.hypertts.anki_utils.run_on_main(self.batch_interrupted_button_setup)

        

# factory and setup functions for ComponentBatch: only use those to create a ComponentBatch
# =========================================================================================

class BatchDialog(aqt.qt.QDialog):
    def __init__(self, hypertts):
        super(aqt.qt.QDialog, self).__init__()
        self.hypertts = hypertts
        self.setWindowTitle(constants.GUI_COLLECTION_DIALOG_TITLE)
        self.main_layout = aqt.qt.QVBoxLayout(self)        

    def configure_browser_existing_preset(self, note_id_list, preset_id: str):
        self.batch_component = ComponentBatch(self.hypertts, self)
        self.batch_component.configure_browser(note_id_list)
        self.batch_component.draw(self.main_layout)
        self.batch_component.load_preset(preset_id)
        self.batch_component.collapse_settings()           

    def configure_browser_new_preset(self, note_id_list, new_preset_name: str):
        self.batch_component = ComponentBatch(self.hypertts, self)
        self.batch_component.configure_browser(note_id_list)
        self.batch_component.new_preset(new_preset_name)
        self.batch_component.draw(self.main_layout)
        self.batch_component.display_settings()

    def configure_editor_new_preset(self, editor_context: config_models.EditorContext):
        batch_component = ComponentBatch(self.hypertts, self)
        batch_component.configure_editor(editor_context)
        new_preset_name = self.hypertts.get_next_preset_name()
        batch_component.new_preset(new_preset_name)
        batch_component.draw(self.main_layout)
        batch_component.no_settings_editor()
        self.batch_component = batch_component

    def configure_editor_existing_preset(self, editor_context: config_models.EditorContext, preset_id: str):
        batch_component = ComponentBatch(self.hypertts, self)
        batch_component.configure_editor(editor_context)
        batch_component.draw(self.main_layout)
        batch_component.load_preset(preset_id)
        batch_component.no_settings_editor()
        self.batch_component = batch_component        

    def verify_profile_saved(self):
        self.batch_component.save_profile_if_changed()

    def closeEvent(self, evnt):
        self.verify_profile_saved()
        super(aqt.qt.QDialog, self).closeEvent(evnt)

    def close(self):
        self.verify_profile_saved()
        self.closed = True
        self.accept()

def create_component_batch_browser_existing_preset(hypertts, note_id_list, preset_id: str) -> ComponentBatch:
    if len(note_id_list) == 0:
        raise errors.NoNotesSelected()
    dialog = BatchDialog(hypertts)
    dialog.configure_browser_existing_preset(note_id_list, preset_id)
    hypertts.anki_utils.wait_for_dialog_input(dialog, constants.DIALOG_ID_BATCH)

def create_component_batch_browser_new_preset(hypertts, note_id_list, new_preset_name: str) -> ComponentBatch:
    if len(note_id_list) == 0:
        raise errors.NoNotesSelected()    
    dialog = BatchDialog(hypertts)
    dialog.configure_browser_new_preset(note_id_list, new_preset_name)
    hypertts.anki_utils.wait_for_dialog_input(dialog, constants.DIALOG_ID_BATCH)

def create_dialog_editor_existing_preset(hypertts, editor_context: config_models.EditorContext, preset_id: str):
    dialog = BatchDialog(hypertts)
    dialog.configure_editor_existing_preset(editor_context, preset_id)
    hypertts.anki_utils.wait_for_dialog_input(dialog, constants.DIALOG_ID_BATCH)    

def create_dialog_editor_new_preset(hypertts, editor_context: config_models.EditorContext):
    """get a new preset_id from the editor, and return the new preset_id"""
    dialog = BatchDialog(hypertts)
    dialog.configure_editor_new_preset(editor_context)
    hypertts.anki_utils.wait_for_dialog_input(dialog, constants.DIALOG_ID_BATCH)
    return dialog.batch_component.editor_new_preset_id