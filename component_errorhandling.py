import sys
import aqt.qt

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)


class ErrorHandling(component_common.ConfigComponentBase):

    def __init__(self, hypertts, dialog, model_change_callback):
        self.hypertts = hypertts
        self.dialog = dialog
        self.model = config_models.ErrorHandling()
        self.model_change_callback = model_change_callback
        self.propagate_model_change = True

        self.realtime_tts_errors_dialog_type = aqt.qt.QComboBox()
        # populate combo box with constants.ErrorDialogType
        for error_dialog_type in constants.ErrorDialogType:
            self.realtime_tts_errors_dialog_type.addItem(error_dialog_type.name, error_dialog_type)

    def get_model(self):
        return self.model

    def load_model(self, model):
        self.model = model
        self.propagate_model_change = False
        self.realtime_tts_errors_dialog_type.setCurrentText(self.model.realtime_tts_errors_dialog_type.name)
        self.propagate_model_change = True

    def notify_model_update(self):
        if self.propagate_model_change == True:
            self.model_change_callback(self.model)

    def draw(self):
        layout_widget = aqt.qt.QWidget()
        layout = aqt.qt.QVBoxLayout(layout_widget)

        # editor add audio
        # ================

        groupbox = aqt.qt.QGroupBox('Realtime TTS Errors')
        vlayout = aqt.qt.QVBoxLayout()

        realtime_tts_error_dialog = aqt.qt.QLabel(constants.GUI_TEXT_ERROR_HANDLING_REALTIME_TTS)
        realtime_tts_error_dialog.setWordWrap(True)
        vlayout.addWidget(realtime_tts_error_dialog)
        vlayout.addWidget(self.realtime_tts_errors_dialog_type)

        groupbox.setLayout(vlayout)
        layout.addWidget(groupbox)

        layout.addStretch()

        # wire events
        self.realtime_tts_errors_dialog_type.currentIndexChanged.connect(self.realtime_tts_errors_dialog_type_changed)

        return layout_widget

    def realtime_tts_errors_dialog_type_changed(self, index):
        logger.info(f'realtime_tts_errors_dialog_type_changed {index}')
        self.model.realtime_tts_errors_dialog_type = self.realtime_tts_errors_dialog_type.itemData(index)
        self.notify_model_update()

