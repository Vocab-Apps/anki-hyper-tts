import sys
import logging
import PyQt5
import time


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
        model = self.note.note_type()
        template = model["tmpls"]
        card = self.hypertts.anki_utils.create_card_from_note(self.note, self.card_ord, model, template)
        if self.side == constants.AnkiCardSide.Front:
            tags = card.question_av_tags()
        elif self.side == constants.AnkiCardSide.Back:
            tags = card.answer_av_tags()
        logging.info(f'av_tags: {tags}')

    def draw(self):
        # populate processed text

        self.batch_label_layout = PyQt5.QtWidgets.QVBoxLayout()

        self.batch_label_layout.addWidget(self.batch_label)
        self.batch_label_layout.addWidget(self.source_preview_label)
        return self.batch_label_layout
