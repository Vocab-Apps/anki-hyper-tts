import aqt.qt
import logging
import copy

import testing_utils

logger = logging.getLogger(__name__)

class EmptyDialog(aqt.qt.QDialog):
    def __init__(self):
        super(aqt.qt.QDialog, self).__init__()
        self.closed = None

    def setupUi(self):
        self.main_layout = aqt.qt.QVBoxLayout(self)

    def getLayout(self):
        return self.main_layout

    def setLayout(self, layout):
        self.main_layout = layout

    def addChildLayout(self, layout):
        self.main_layout.addLayout(layout)

    def addChildWidget(self, widget):
        self.main_layout.addWidget(widget)
    
    def close(self):
        self.closed = True


def build_empty_dialog() -> EmptyDialog:
    dialog = EmptyDialog()
    dialog.setupUi()
    return dialog

class MockModelChangeCallback():
    def __init__(self):
        self.model = None

    def model_updated(self, model):
        logger.info('MockModelChangeCallback.model_updated')
        self.model = copy.deepcopy(model)

class MockBatchPreviewCallback():
    def __init__(self):
        self.sample_text = None
        self.batch_start_called = None
        self.batch_end_called = None

    def sample_selected(self, note_id, text):
        self.note_id = note_id
        self.sample_text = text

    def batch_start(self):
        self.batch_start_called = True

    def batch_end(self, completed):
        self.batch_end_called = True


def get_hypertts_instance():
    # return hypertts_instance    
    config_gen = testing_utils.TestConfigGenerator()
    return config_gen.build_hypertts_instance_test_servicemanager('default')