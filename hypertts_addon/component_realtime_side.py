import sys
import aqt.qt

from . import component_common
from . import component_realtime_source
from . import component_voiceselection
from . import component_text_processing
from . import config_models
from . import constants
from . import errors
from . import gui_utils
from . import text_utils
from . import logging_utils
logger = logging_utils.get_child_logger(__name__)


class ComponentRealtimeSide(component_common.ConfigComponentBase):
    MIN_WIDTH_COMPONENT = 600
    MIN_HEIGHT = 400

    def __init__(self, hypertts, dialog, side, card_ord, model_change_callback, existing_preset_fn):
        self.hypertts = hypertts
        self.dialog = dialog
        self.side = side
        self.card_ord = card_ord
        self.model_change_callback = model_change_callback
        self.model = config_models.RealtimeConfigSide()
        self.side_enabled = False
        self.existing_preset_fn = existing_preset_fn

        # create certain widgets upfront
        self.side_enabled_checkbox = aqt.qt.QCheckBox(f'Enable Realtime TTS for {self.side.name} side')

        self.text_preview_label = aqt.qt.QLabel()
        self.text_preview_label.setWordWrap(True)

        self.preview_sound_button = aqt.qt.QPushButton('Preview Sound')

    def configure_note(self, note):
        self.note = note
        field_list = self.hypertts.get_fields_from_note(self.note)
        self.source = component_realtime_source.RealtimeSource(self.hypertts, field_list, self.source_model_updated)
        self.voice_selection = component_voiceselection.VoiceSelection(self.hypertts, self.dialog, self.voice_selection_model_updated)
        self.text_processing = component_text_processing.TextProcessing(self.hypertts, self.text_processing_model_updated)

    def load_existing_preset(self):
        existing_preset_name = self.hypertts.card_template_has_tts_tag(self.note, self.side, self.card_ord)
        if existing_preset_name != None:
            self.existing_preset_fn(existing_preset_name)
            realtime_model = self.hypertts.load_realtime_config(existing_preset_name)
            if self.side == constants.AnkiCardSide.Front:
                logger.info(f'loading realtime_model.front: {realtime_model.front}')
                self.load_model(realtime_model.front)
            else:
                logger.info(f'loading realtime_model.back: {realtime_model.back}')
                self.load_model(realtime_model.back)

    def load_batch(self, batch_name):
        batch = self.hypertts.load_batch_config(batch_name)
        self.load_model(batch)

    def load_model(self, model):
        self.model = model
        # is this side enabled
        self.side_enabled_checkbox.setChecked(model.side_enabled)
        # disseminate to all components
        logger.info(f'loading source model: {model.source}')
        self.source.load_model(model.source)
        self.voice_selection.load_model(model.voice_selection)
        self.text_processing.load_model(model.text_processing)
        self.update_preview()

    def get_model(self):
        return self.model

    def source_model_updated(self, model):
        logger.info(f'source_model_updated: {model}')
        self.model.source = model
        self.model_part_updated_common()

    def voice_selection_model_updated(self, model):
        logger.info('voice_selection_model_updated')
        self.model.voice_selection = model
        self.model_part_updated_common()

    def text_processing_model_updated(self, model):
        logger.info('text_processing_model_updated')
        self.model.text_processing = model
        self.model_part_updated_common()

    def model_part_updated_common(self):
        self.update_preview()
        self.notify_model_update()

    def notify_model_update(self):
        self.model_change_callback(self.model)

    def update_preview(self):
        logger.info('update_preview')
        try:
            # does the realtime model pass validation ?
            if self.get_model().side_enabled:
                tts_tags = self.hypertts.render_card_template_extract_tts_tag(self.get_model(),
                    self.note, self.side, self.card_ord)
                self.preview_process_tts_tags(tts_tags)
        except errors.ModelValidationError as e:
            error_message = f'model validation error: {e}'
            self.text_preview_label.setText(error_message)

    def preview_process_tts_tags(self, tts_tags):
        logger.info('preview_process_tts_tags')
        # retain elements which are TTS tags
        tts_tags = self.hypertts.anki_utils.extract_tts_tags(tts_tags)
        if len(tts_tags) == 0:
            logger.error('no TTS tags found')
            return []
            # raise Exception('no TTS tags found')
        if len(tts_tags) > 1:
            logger.error('more than one TTS tag found')
            return []
            # raise Exception(f'more than one TTS tag found: {str(tts_tags)}')
        tts_tag = tts_tags[0]
        try:
            processed_text = text_utils.process_text(tts_tag.field_text, self.get_model().text_processing)
            self.text_preview_label.setText(processed_text)
        except errors.HyperTTSError as e:
            warning_message = f'could not process text: {str(e)}'
            logger.warning(warning_message)
            self.text_preview_label.setText(warning_message)
        except Exception as e:
            error_message = f'could not process text: {str(e)}'
            logger.error(error_message)
            self.text_preview_label.setText(error_message)

    def side_enabled_change(self, checkbox_value):
        self.side_enabled = checkbox_value == 2
        logger.info(f'side_enabled: {self.side_enabled}')
        self.tabs.setEnabled(self.side_enabled)
        self.preview_groupbox.setEnabled(self.side_enabled)
        self.model.side_enabled = self.side_enabled
        self.model_part_updated_common()

    def sample_selected(self, note_id, text):
        self.voice_selection.sample_text_selected(text)
        self.note = self.hypertts.anki_utils.get_note_by_id(note_id)
        self.preview_sound_button.setEnabled(True)
        self.preview_sound_button.setText('Preview Sound')


    def draw(self):
        self.vlayout = aqt.qt.QVBoxLayout()

        # side enabled checkbox
        # =====================
        
        self.side_enabled_checkbox.setFont(gui_utils.get_large_checkbox_font())
        self.vlayout.addWidget(self.side_enabled_checkbox)

        # preset settings tabs
        # ====================

        self.tabs = aqt.qt.QTabWidget()

        self.tabs.addTab(self.source.draw(), 'Source')
        self.tabs.addTab(self.voice_selection.draw(), 'Voice Selection')
        self.tabs.addTab(self.text_processing.draw(), 'Text Processing')

        # self.tabs.setEnabled(False)

        self.vlayout.addWidget(self.tabs)

        # add preview box
        # ===============

        self.preview_groupbox = aqt.qt.QGroupBox('Preview')
        preview_vlayout = aqt.qt.QVBoxLayout()
        source_preview_label = aqt.qt.QLabel('Text to be pronounced:')
        preview_vlayout.addWidget(source_preview_label)
        preview_vlayout.addWidget(self.text_preview_label)
        preview_vlayout.addWidget(self.preview_sound_button)

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
        logger.info('sound_preview_button_pressed')
        self.preview_sound_button.setText('Playing Preview...')
        self.preview_sound_button.setEnabled(False)
        self.hypertts.anki_utils.run_in_background(self.sound_preview_task, self.sound_preview_task_done)

    def sound_preview_task(self):
        logger.info('sound_preview_task')
        tts_tags = self.hypertts.render_card_template_extract_tts_tag(self.get_model(),
            self.note, self.side, self.card_ord)
        text = tts_tags[0].field_text
        logger.info(f'playing text: [{text}]')
        self.hypertts.play_realtime_audio(self.get_model(), text)
        return True

    def sound_preview_task_done(self, result):
        logger.info('sound_preview_task_done')
        with self.hypertts.error_manager.get_single_action_context('Playing Realtime Sound Preview'):
            result = result.result()
        self.hypertts.anki_utils.run_on_main(self.finish_sound_preview)

    def finish_sound_preview(self):
        self.preview_sound_button.setEnabled(True)
        self.preview_sound_button.setText('Preview Sound')


        