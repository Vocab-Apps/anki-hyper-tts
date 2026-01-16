import sys
import aqt.qt

from . import component_common
from . import config_models
from . import constants
from . import gui_utils
from . import logging_utils
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

        self.error_stats_reporting = aqt.qt.QCheckBox('Send anonymous usage statistics and error reports to help improve HyperTTS')

        self.disable_ssl_verification = aqt.qt.QCheckBox('Disable SSL certificate verification (not recommended)')

    def get_model(self):
        return self.model

    def load_model(self, model):
        self.model = model
        self.propagate_model_change = False
        self.realtime_tts_errors_dialog_type.setCurrentText(self.model.realtime_tts_errors_dialog_type.name)
        self.error_stats_reporting.setChecked(self.model.error_stats_reporting)
        self.disable_ssl_verification.setChecked(self.model.disable_ssl_verification)
        self.propagate_model_change = True

    def notify_model_update(self):
        if self.propagate_model_change == True:
            self.model_change_callback(self.model)

    def draw(self):
        layout_widget = aqt.qt.QWidget()
        layout = aqt.qt.QVBoxLayout(layout_widget)

        # editor add audio
        # ================

        # Realtime TTS Errors group
        realtime_groupbox = aqt.qt.QGroupBox('Realtime TTS Errors')
        realtime_vlayout = aqt.qt.QVBoxLayout()

        realtime_tts_error_dialog = aqt.qt.QLabel(constants.GUI_TEXT_ERROR_HANDLING_REALTIME_TTS)
        realtime_tts_error_dialog.setWordWrap(True)
        realtime_vlayout.addWidget(realtime_tts_error_dialog)
        realtime_vlayout.addWidget(self.realtime_tts_errors_dialog_type)

        realtime_groupbox.setLayout(realtime_vlayout)
        layout.addWidget(realtime_groupbox)

        # Error Reporting group
        reporting_groupbox = aqt.qt.QGroupBox('Error Reporting')
        reporting_vlayout = aqt.qt.QVBoxLayout()
        reporting_vlayout.addWidget(self.error_stats_reporting)
        reporting_groupbox.setLayout(reporting_vlayout)
        layout.addWidget(reporting_groupbox)

        # Network Connection group
        network_groupbox = aqt.qt.QGroupBox('Network Connection')
        network_vlayout = aqt.qt.QVBoxLayout()
        ssl_description = aqt.qt.QLabel('Only disable SSL verification if you are behind a corporate proxy or firewall that intercepts HTTPS connections.')
        ssl_description.setWordWrap(True)
        network_vlayout.addWidget(ssl_description)
        network_vlayout.addWidget(self.disable_ssl_verification)
        network_groupbox.setLayout(network_vlayout)
        layout.addWidget(network_groupbox)

        layout.addStretch()

        # wire events
        self.realtime_tts_errors_dialog_type.currentIndexChanged.connect(self.realtime_tts_errors_dialog_type_changed)
        self.error_stats_reporting.stateChanged.connect(self.error_stats_reporting_changed)
        self.disable_ssl_verification.stateChanged.connect(self.disable_ssl_verification_changed)

        return layout_widget

    def realtime_tts_errors_dialog_type_changed(self, index):
        logger.info(f'realtime_tts_errors_dialog_type_changed {index}')
        self.model.realtime_tts_errors_dialog_type = self.realtime_tts_errors_dialog_type.itemData(index)
        self.notify_model_update()

    def error_stats_reporting_changed(self, state):
        logger.info(f'error_stats_reporting_changed {state}')
        self.model.error_stats_reporting = bool(state)
        self.notify_model_update()

    def disable_ssl_verification_changed(self, state):
        logger.info(f'disable_ssl_verification_changed {state}')
        self.model.disable_ssl_verification = bool(state)
        self.notify_model_update()

