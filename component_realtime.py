import sys
import PyQt5
import logging

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
component_realtime_source = __import__('component_realtime_source', globals(), locals(), [], sys._addon_import_level_base)
component_voiceselection = __import__('component_voiceselection', globals(), locals(), [], sys._addon_import_level_base)
component_text_processing = __import__('component_text_processing', globals(), locals(), [], sys._addon_import_level_base)
component_realtime_preview = __import__('component_realtime_preview', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)


class ComponentRealtime(component_common.ConfigComponentBase):
    MIN_WIDTH_COMPONENT = 600
    MIN_HEIGHT = 400

    def __init__(self, hypertts, dialog, side):
        self.hypertts = hypertts
        self.dialog = dialog
        self.side = side
        self.model = config_models.RealtimeConfig()

        # create certain widgets upfront
        self.preview_sound_button = PyQt5.QtWidgets.QPushButton('Preview Sound')
        self.apply_button = PyQt5.QtWidgets.QPushButton('Apply to Notes')
        self.cancel_button = PyQt5.QtWidgets.QPushButton('Cancel')

    def configure_note(self, note):
        self.note = note
        field_list = self.hypertts.get_fields_from_note(self.note)
        self.source = component_realtime_source.RealtimeSource(self.hypertts, field_list, self.source_model_updated)
        self.voice_selection = component_voiceselection.VoiceSelection(self.hypertts, self.voice_selection_model_updated)
        self.text_processing = component_text_processing.TextProcessing(self.hypertts, self.text_processing_model_updated)
        self.preview = component_realtime_preview.RealtimePreview(self.hypertts, self.note)

    def load_batch(self, batch_name):
        batch = self.hypertts.load_batch_config(batch_name)
        self.load_model(batch)

    def load_model(self, model):
        self.model = model
        # disseminate to all components
        self.source.load_model(model.source)
        self.voice_selection.load_model(model.voice_selection)
        self.text_processing.load_model(model.text_processing)
        self.preview.load_model(self.get_model())

    def get_model(self):
        return self.model

    def source_model_updated(self, model):
        logging.info(f'source_model_updated: {model}')
        self.model.source = model
        self.model_part_updated_common()

    def voice_selection_model_updated(self, model):
        logging.info('voice_selection_model_updated')
        self.model.voice_selection = model
        self.model_part_updated_common()

    def text_processing_model_updated(self, model):
        logging.info('text_processing_model_updated')
        self.model.text_processing = model
        self.model_part_updated_common()

    def model_part_updated_common(self):
        self.preview.load_model(self.get_model())


    def sample_selected(self, note_id, text):
        self.voice_selection.sample_text_selected(text)
        self.note = self.hypertts.anki_utils.get_note_by_id(note_id)
        self.preview_sound_button.setEnabled(True)
        self.preview_sound_button.setText('Preview Sound')


    def draw(self, layout):
        self.vlayout = PyQt5.QtWidgets.QVBoxLayout()

        # header
        # ======

        hlayout = PyQt5.QtWidgets.QHBoxLayout()

        # logo header
        hlayout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        self.vlayout.addLayout(hlayout)

        # preset settings tabs
        # ====================

        self.tabs = PyQt5.QtWidgets.QTabWidget()
        self.tab_source = PyQt5.QtWidgets.QWidget()
        self.tab_voice_selection = PyQt5.QtWidgets.QWidget()
        self.tab_text_processing = PyQt5.QtWidgets.QWidget()

        self.tab_source.setLayout(self.source.draw())
        self.tab_voice_selection.setLayout(self.voice_selection.draw())
        self.tab_text_processing.setLayout(self.text_processing.draw())

        self.tabs.addTab(self.tab_source, 'Source')
        self.tabs.addTab(self.tab_voice_selection, 'Voice Selection')
        self.tabs.addTab(self.tab_text_processing, 'Text Processing')

        self.splitter = PyQt5.QtWidgets.QSplitter(PyQt5.QtCore.Qt.Horizontal)
        self.splitter.addWidget(self.tabs)

        self.preview_widget = PyQt5.QtWidgets.QWidget()
        self.preview_widget.setLayout(self.preview.draw())
        self.splitter.addWidget(self.preview_widget)
        self.vlayout.addWidget(self.splitter)


        self.vlayout.addStretch()

        # setup bottom buttons
        # ====================

        hlayout = PyQt5.QtWidgets.QHBoxLayout()
        hlayout.addStretch()

        # apply button
        apply_label_text = 'Apply To Note'
        self.apply_button.setText(apply_label_text)
        self.apply_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        hlayout.addWidget(self.apply_button)
        # cancel button
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        hlayout.addWidget(self.cancel_button)
        self.vlayout.addLayout(hlayout)

        self.preview_sound_button.pressed.connect(self.sound_preview_button_pressed)
        self.apply_button.pressed.connect(self.apply_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        self.cancel_button.setFocus()

        layout.addLayout(self.vlayout)

    def sound_preview_button_pressed(self):
        self.disable_bottom_buttons()
        self.preview_sound_button.setText('Playing Preview...')
        self.hypertts.anki_utils.run_in_background(self.sound_preview_task, self.sound_preview_task_done)

    def apply_button_pressed(self):
        with self.hypertts.error_manager.get_single_action_context('Applying Audio to Notes'):
            self.get_model().validate()
            logging.info('apply_button_pressed')
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
        self.hypertts.editor_note_add_audio(self.batch_model, self.editor, self.note, self.add_mode)
        return True

    def apply_note_editor_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Adding Audio to Note'):
            result = result.result()
            self.dialog.close()
        self.hypertts.anki_utils.run_on_main(self.finish_apply_note_editor)
    
    def finish_apply_note_editor(self):
        self.enable_bottom_buttons()
        self.apply_button.setText('Apply To Note')

    def sound_preview_task(self):
        self.hypertts.preview_note_audio(self.batch_model, self.note)
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

        