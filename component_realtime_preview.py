import sys
import logging
import PyQt5
import time
import pprint
import copy


constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
batch_status = __import__('batch_status', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)

class RealtimePreview(component_common.ComponentBase):
    def __init__(self, hypertts, note, side, card_ord):
        self.hypertts = hypertts
        self.note = note
        self.side = side
        self.card_ord = card_ord
        self.batch_label = PyQt5.QtWidgets.QLabel()
        self.source_preview_label = PyQt5.QtWidgets.QLabel('preview')
        self.source_preview_label.setWordWrap(True)

    def load_model(self, model):
        self.model = model
        logging.info(f'load_model: {self.model}')
        self.update_preview()
        return
        try:
            self.batch_model = model
            self.batch_label.setText(str(self.batch_model))
            if self.batch_model.text_processing != None:
                source_text, processed_text = self.hypertts.get_source_processed_text(self.note, self.batch_model.source, self.batch_model.text_processing)
                self.source_preview_label.setText(f'<b>Generating Audio for:</b> {processed_text}')
        except errors.HyperTTSError as error:
            message = f'<b>Encountered Error:</b> {str(error)}'
            self.source_preview_label.setText(message)

    def update_preview(self):
        # does the realtime model pass validation ?
        try:
            self.model.validate()
            model = self.note.note_type()
            template = model["tmpls"][self.card_ord]
            template = copy.deepcopy(template)
            tts_tag = self.hypertts.build_realtime_tts_tag(self.model)
            logging.info(f'tts tag: {tts_tag}')
            template['qfmt'] += tts_tag
            pprint.pprint(template)
            card = self.hypertts.anki_utils.create_card_from_note(self.note, self.card_ord, model, template)
            if self.side == constants.AnkiCardSide.Front:
                self.preview_process_tts_tags(card.question_av_tags())
            elif self.side == constants.AnkiCardSide.Back:
                self.preview_process_tts_tags(card.answer_av_tags())
        except errors.ModelValidationError as e:
            error_message = f'model validation error: {e}'
            self.source_preview_label.setText(error_message)
            # logging.error(f'model validation error: {e}')

    def preview_process_tts_tags(self, av_tags):
        # retain elements which are TTS tags
        tts_tags = self.hypertts.anki_utils.extract_tts_tags(av_tags)
        if len(tts_tags) == 0:
            raise Exception('no TTS tags found')
        if len(tts_tags) > 1:
            raise Exception(f'more than one TTS tag found: {str(tts_tags)}')
        tts_tag = tts_tags[0]
        self.source_preview_label.setText(tts_tag.field_text)

    def draw(self):
        # populate processed text

        self.batch_label_layout = PyQt5.QtWidgets.QVBoxLayout()

        self.batch_label_layout.addWidget(self.batch_label)
        self.batch_label_layout.addWidget(self.source_preview_label)
        return self.batch_label_layout
