import sys
import logging
import PyQt5
import time


constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
batch_status = __import__('batch_status', globals(), locals(), [], sys._addon_import_level_base)

class LabelPreview(component_common.ComponentBase):
    def __init__(self, hypertts, note):
        self.hypertts = hypertts
        self.note = note
        self.batch_label = PyQt5.QtWidgets.QLabel()
        self.source_preview_label = PyQt5.QtWidgets.QLabel()

    def load_model(self, model):
        self.batch_model = model
        self.batch_label.setText(str(self.batch_model))
        source_text, processed_text = self.hypertts.get_source_processed_text(self.note, self.batch_model.source)
        self.source_preview_label.setText(f'<b>Generating Audio for:</b> {processed_text}')

    def draw(self):
        # populate processed text

        self.batch_label_layout = PyQt5.QtWidgets.QVBoxLayout()

        self.batch_label_layout.addWidget(self.batch_label)
        self.batch_label_layout.addWidget(self.source_preview_label)
        return self.batch_label_layout
