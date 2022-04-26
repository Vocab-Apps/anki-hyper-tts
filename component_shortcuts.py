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

        hlayout = aqt.qt.QHBoxLayout()

        self.editor_add_audio_key_sequence = aqt.qt.QKeySequenceEdit()
        hlayout.addWidget(self.editor_add_audio_key_sequence)

        editor_add_audio_clear_button = aqt.qt.QPushButton('Clear')
        hlayout.addWidget(editor_add_audio_clear_button)
        
        vlayout.addLayout(hlayout)

        groupbox.setLayout(vlayout)
        layout.addWidget(groupbox)

        # editor preview audio
        # ====================

        groupbox = aqt.qt.QGroupBox('Editor Preview Audio')
        vlayout = aqt.qt.QVBoxLayout()

        editor_preview_audio_label = aqt.qt.QLabel(constants.GUI_TEXT_SHORTCUTS_EDITOR_PREVIEW_AUDIO)
        editor_preview_audio_label.setWordWrap(True)
        vlayout.addWidget(editor_preview_audio_label)

        hlayout = aqt.qt.QHBoxLayout()

        self.editor_preview_audio_key_sequence = aqt.qt.QKeySequenceEdit()
        hlayout.addWidget(self.editor_preview_audio_key_sequence)

        editor_preview_audio_clear_button = aqt.qt.QPushButton('Clear')
        hlayout.addWidget(editor_preview_audio_clear_button)

        vlayout.addLayout(hlayout)

        groupbox.setLayout(vlayout)
        layout.addWidget(groupbox)

        # warning label
        note_label = aqt.qt.QLabel(constants.GUI_TEXT_SHORTCUTS_ANKI_RESTART)
        note_label.setWordWrap(True)
        layout.addWidget(note_label)

        layout.addStretch()

        # wire events
        editor_add_audio_clear_button.pressed.connect(self.editor_add_audio_clear)
        editor_preview_audio_clear_button.pressed.connect(self.editor_preview_audio_clear)
        
        self.editor_add_audio_key_sequence.keySequenceChanged.connect(self.editor_add_audio_changed)
        self.editor_preview_audio_key_sequence.keySequenceChanged.connect(self.editor_preview_audio_changed)


    def editor_add_audio_clear(self):
        self.editor_add_audio_key_sequence.clear()

    def editor_preview_audio_clear(self):
        self.editor_preview_audio_key_sequence.clear()

    def editor_add_audio_changed(self, key_sequence):
        logger.info(f'editor_add_audio_changed {key_sequence}')
        logger.info(f'key_sequence.toString(): {key_sequence.toString()}')

    def editor_preview_audio_changed(self, key_sequence):
        logger.info(f'editor_preview_audio_changed')
        logger.info(f'key_sequence.toString(): {key_sequence.toString()}')        
