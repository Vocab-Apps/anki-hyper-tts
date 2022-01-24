import sys
import logging
import PyQt5
import time


constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
batch_status = __import__('batch_status', globals(), locals(), [], sys._addon_import_level_base)

class LabelPreview(component_common.ComponentBase):
    def __init__(self, hypertts):
        self.hypertts = hypertts

    def load_model(self, model):
        self.batch_model = model

    def draw(self):
        # populate processed text

        self.batch_label_layout = PyQt5.QtWidgets.QVBoxLayout()
        self.batch_label = PyQt5.QtWidgets.QLabel()
        self.batch_label_layout.addWidget(self.batch_label)

        return self.batch_label_layout
