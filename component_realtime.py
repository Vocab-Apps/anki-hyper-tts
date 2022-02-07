import sys
import PyQt5
import logging
import copy

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
component_realtime_side = __import__('component_realtime_side', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)


class ComponentRealtime(component_common.ConfigComponentBase):
    MIN_WIDTH_COMPONENT = 600
    MIN_HEIGHT = 400

    def __init__(self, hypertts, dialog, card_ord):
        self.hypertts = hypertts
        self.dialog = dialog
        self.card_ord = card_ord
        self.model = config_models.RealtimeConfig()

        self.apply_button = PyQt5.QtWidgets.QPushButton('Apply to Notes')
        self.cancel_button = PyQt5.QtWidgets.QPushButton('Cancel')

    def configure_note(self, note):
        self.note = note
        self.front = component_realtime_side.ComponentRealtimeSide(self.hypertts, 
            constants.AnkiCardSide.Front, self.card_ord, self.front_model_updated)
        self.back = component_realtime_side.ComponentRealtimeSide(self.hypertts, 
            constants.AnkiCardSide.Back, self.card_ord, self.back_model_updated)
        self.front.configure_note(note)
        self.back.configure_note(note)

    def load_model(self, model):
        self.model = model
        # disseminate to all components
        self.front.load_model(model.front)
        self.back.load_model(model.back)

    def get_model(self):
        return self.model

    def front_model_updated(self, model):
        logging.info('front_model_updated')
        self.model.front = model

    def back_model_updated(self, model):
        logging.info('back_model_update')
        self.model.back = model

    def draw(self, layout):
        self.vlayout = PyQt5.QtWidgets.QVBoxLayout()

        # header
        # ======

        hlayout = PyQt5.QtWidgets.QHBoxLayout()

        # logo header
        hlayout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        self.vlayout.addLayout(hlayout)

        # sides tabs
        # ==========

        self.tabs = PyQt5.QtWidgets.QTabWidget()
        self.tabs.setTabPosition(PyQt5.QtWidgets.QTabWidget.West)
        self.tab_front = PyQt5.QtWidgets.QWidget()
        self.tab_back = PyQt5.QtWidgets.QWidget()

        self.tab_front.setLayout(self.front.draw())
        self.tab_back.setLayout(self.back.draw())

        self.tabs.addTab(self.tab_front, 'Front Side')
        self.tabs.addTab(self.tab_back, 'Back Side')

        # self.tabs.setEnabled(False)

        self.vlayout.addWidget(self.tabs)


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

        # wire events
        self.apply_button.pressed.connect(self.apply_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        # defaults
        self.cancel_button.setFocus()

        layout.addLayout(self.vlayout)

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

        