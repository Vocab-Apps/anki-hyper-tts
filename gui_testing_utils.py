import aqt.qt
import logging
import copy

import testing_utils
import config_models

logger = logging.getLogger(__name__)

def get_editor_context():
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    model_id=config_gen.model_id_chinese
    deck_id=config_gen.deck_id

    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    mock_editor = config_gen.get_mock_editor_with_note(note_1.id, deck_id, False)

    deck_note_type: config_models.DeckNoteType = config_models.DeckNoteType(
        model_id=model_id,
        deck_id=deck_id)

    editor_context = config_models.EditorContext(
        editor=mock_editor, note=note_1, add_mode=False, selected_text=None, selected_text_fieldname=None)

    return hypertts_instance, deck_note_type, editor_context

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

class EmptyGridLayoutDialog(aqt.qt.QDialog):
    def __init__(self):
        super(aqt.qt.QDialog, self).__init__()
        self.closed = None

    def setupUi(self):
        self.grid_layout = aqt.qt.QGridLayout(self)

    def getLayout(self):
        return self.grid_layout

    def setLayout(self, layout):
        self.grid_layout = layout

    def addChildLayout(self, layout):
        self.grid_layout.addLayout(layout)

    def addChildWidget(self, widget):
        self.grid_layout.addWidget(widget)
    
    def close(self):
        self.closed = True        


def build_empty_dialog() -> EmptyDialog:
    dialog = EmptyDialog()
    dialog.setupUi()
    return dialog

def build_empty_gridlayout_dialog() -> EmptyDialog:
    dialog = EmptyGridLayoutDialog()
    dialog.setupUi()
    return dialog

class MockModelChangeCallback():
    def __init__(self):
        self.model = None

    def model_updated(self, model):
        logger.info('MockModelChangeCallback.model_updated')
        self.model = copy.deepcopy(model)

class MockModelDeleteCallback():
    def __init__(self):
        pass

    def model_delete(self):
        logger.info('MockModelDeleteCallback.model_delete')

class MockRequestStartedCallback():
    def __init__(self):
        pass

    def request_started(self):
        logger.info('MockRequestStartedCallback.model_delete')        

class MockRequestFinishedCallback():
    def __init__(self):
        pass

    def request_finished(self):
        logger.info('MockRequestFinishedCallback.request_finished')

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