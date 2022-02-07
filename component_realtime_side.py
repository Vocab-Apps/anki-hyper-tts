import sys
import PyQt5
import logging
import copy

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
component_realtime_source = __import__('component_realtime_source', globals(), locals(), [], sys._addon_import_level_base)
component_voiceselection = __import__('component_voiceselection', globals(), locals(), [], sys._addon_import_level_base)
component_text_processing = __import__('component_text_processing', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)


class ComponentRealtimeSide(component_common.ConfigComponentBase):
    MIN_WIDTH_COMPONENT = 600
    MIN_HEIGHT = 400

    def __init__(self, hypertts, side, card_ord, model_change_callback):
        self.hypertts = hypertts
        self.side = side
        self.card_ord = card_ord
        self.model_change_callback = model_change_callback
        self.model = config_models.RealtimeConfigSide()
        self.side_enabled = False

        # create certain widgets upfront
        self.side_enabled_checkbox = PyQt5.QtWidgets.QCheckBox(f'Enable Realtime TTS for {self.side.name} side')

        self.text_preview_label = PyQt5.QtWidgets.QLabel()

        self.preview_sound_button = PyQt5.QtWidgets.QPushButton('Preview Sound')
        self.apply_button = PyQt5.QtWidgets.QPushButton('Apply to Notes')
        self.cancel_button = PyQt5.QtWidgets.QPushButton('Cancel')

    def configure_note(self, note):
        self.note = note
        field_list = self.hypertts.get_fields_from_note(self.note)
        self.source = component_realtime_source.RealtimeSource(self.hypertts, field_list, self.source_model_updated)
        self.voice_selection = component_voiceselection.VoiceSelection(self.hypertts, self.voice_selection_model_updated)
        self.text_processing = component_text_processing.TextProcessing(self.hypertts, self.text_processing_model_updated)

    def load_batch(self, batch_name):
        batch = self.hypertts.load_batch_config(batch_name)
        self.load_model(batch)

    def load_model(self, model):
        self.model = model
        # disseminate to all components
        self.source.load_model(model.source)
        self.voice_selection.load_model(model.voice_selection)
        self.text_processing.load_model(model.text_processing)

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
        self.update_preview()
        self.notify_model_update()

    def notify_model_update(self):
        self.model_change_callback(self.model)

    def update_preview(self):
        try:
            # does the realtime model pass validation ?
            tts_tags = self.hypertts.render_card_template_extract_tts_tag(self.get_model(),
            self.note, self.card_ord, self.side)
            self.preview_process_tts_tags(tts_tags)
        except errors.ModelValidationError as e:
            error_message = f'model validation error: {e}'
            self.text_preview_label.setText(error_message)

    def preview_process_tts_tags(self, tts_tags):
        # retain elements which are TTS tags
        tts_tags = self.hypertts.anki_utils.extract_tts_tags(tts_tags)
        if len(tts_tags) == 0:
            logging.error('no TTS tags found')
            return []
            # raise Exception('no TTS tags found')
        if len(tts_tags) > 1:
            logging.error('more than one TTS tag found')
            return []
            # raise Exception(f'more than one TTS tag found: {str(tts_tags)}')
        tts_tag = tts_tags[0]
        self.text_preview_label.setText(tts_tag.field_text)

    def side_enabled_change(self, checkbox_value):
        self.side_enabled = checkbox_value == 2
        logging.info(f'side_enabled: {self.side_enabled}')
        self.tabs.setEnabled(self.side_enabled)
        self.preview_groupbox.setEnabled(self.side_enabled)
        self.model.side_enabled = self.side_enabled
        self.notify_model_update()

    def sample_selected(self, note_id, text):
        self.voice_selection.sample_text_selected(text)
        self.note = self.hypertts.anki_utils.get_note_by_id(note_id)
        self.preview_sound_button.setEnabled(True)
        self.preview_sound_button.setText('Preview Sound')


    def draw(self):
        self.vlayout = PyQt5.QtWidgets.QVBoxLayout()

        # side enabled checkbox
        # =====================
        
        self.side_enabled_checkbox.setFont(gui_utils.get_large_checkbox_font())
        self.vlayout.addWidget(self.side_enabled_checkbox)

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

        # self.tabs.setEnabled(False)

        self.vlayout.addWidget(self.tabs)

        # add preview box
        # ===============

        self.preview_groupbox = PyQt5.QtWidgets.QGroupBox('Preview')
        preview_vlayout = PyQt5.QtWidgets.QVBoxLayout()
        source_preview_label = PyQt5.QtWidgets.QLabel('Text to be pronounced:')
        preview_vlayout.addWidget(source_preview_label)
        preview_vlayout.addWidget(self.text_preview_label)

        self.preview_button = PyQt5.QtWidgets.QPushButton('Preview Sound')
        preview_vlayout.addWidget(self.preview_button)

        self.preview_groupbox.setLayout(preview_vlayout)


        self.vlayout.addWidget(self.preview_groupbox)
        

        # wire events
        self.side_enabled_checkbox.stateChanged.connect(self.side_enabled_change)
        self.preview_sound_button.pressed.connect(self.sound_preview_button_pressed)

        # defaults
        self.tabs.setEnabled(self.side_enabled)
        self.preview_groupbox.setEnabled(self.side_enabled)        

        return self.vlayout

    def sound_preview_button_pressed(self):
        self.preview_sound_button.setText('Playing Preview...')
        self.hypertts.anki_utils.run_in_background(self.sound_preview_task, self.sound_preview_task_done)

    def sound_preview_task(self):
        tts_tags = self.hypertts.render_card_template_extract_tts_tag(self.get_model(),
            self.note, self.card_ord, self.side)
        text = tts_tags[0].field_text
        self.hypertts.play_realtime_audio(self.get_model(), text)
        return True

    def sound_preview_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Playing Realtime Sound Preview'):
            result = result.result()
        self.hypertts.anki_utils.run_on_main(self.finish_sound_preview)

    def finish_sound_preview(self):
        self.preview_sound_button.setText('Preview Sound')


        