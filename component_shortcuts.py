import sys
import aqt.qt

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)


class Shortcuts(component_common.ConfigComponentBase):

    def __init__(self, hypertts, dialog):
        self.hypertts = hypertts
        self.dialog = dialog
        self.model = config_models.Configuration()

    def get_model(self):
        return self.model

    def load_model(self, model):
        self.model = model

    def draw(self, layout):

        # editor add audio
        # ================

        groupbox = aqt.qt.QGroupBox('Editor Add Audio')
        vlayout = aqt.qt.QVBoxLayout()

        editor_add_audio_label = aqt.qt.QLabel(constants.GUI_TEXT_SHORTCUTS_EDITOR_ADD_AUDIO)
        editor_add_audio_label.setWordWrap(True)
        vlayout.addWidget(editor_add_audio_label)

        self.editor_add_audio_key_sequence = aqt.qt.QKeySequenceEdit()
        vlayout.addWidget(self.editor_add_audio_key_sequence)

        editor_add_audio_clear_button = aqt.qt.QPushButton('Clear')
        vlayout.addWidget(editor_add_audio_clear_button)

        groupbox.setLayout(vlayout)
        layout.addWidget(groupbox)

        # editor preview audio
        # ====================

        groupbox = aqt.qt.QGroupBox('Editor Preview Audio')
        vlayout = aqt.qt.QVBoxLayout()

        editor_preview_audio_label = aqt.qt.QLabel(constants.GUI_TEXT_SHORTCUTS_EDITOR_PREVIEW_AUDIO)
        editor_preview_audio_label.setWordWrap(True)
        vlayout.addWidget(editor_preview_audio_label)

        self.editor_preview_audio_key_sequence = aqt.qt.QKeySequenceEdit()
        vlayout.addWidget(self.editor_preview_audio_key_sequence)

        editor_preview_audio_clear_button = aqt.qt.QPushButton('Clear')
        vlayout.addWidget(editor_preview_audio_clear_button)

        groupbox.setLayout(vlayout)
        layout.addWidget(groupbox)

        layout.addStretch()


        # wire events
        editor_add_audio_clear_button.pressed.connect(self.editor_add_audio_clear)




    def editor_add_audio_clear(self):
        self.editor_add_audio_key_sequence.clear()
