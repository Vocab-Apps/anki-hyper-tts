import aqt.qt
from . import config_models
from . import constants
from . import gui_utils
from . import logging_utils
from . import constants_events
from .constants_events import Event, EventMode
from . import stats

logger = logging_utils.get_test_child_logger(__name__)

sc = stats.StatsContext(constants_events.EventContext.services_configuration)

class ServicesConfigurationDialog(aqt.qt.QDialog):
    """Dialog for choosing how to configure HyperTTS services"""
    def __init__(self, hypertts):
        super(aqt.qt.QDialog, self).__init__()
        self.hypertts = hypertts
        self.setupUi()
        self.chosen_mode = None

    def setupUi(self):
        self.setWindowTitle(constants.TITLE_PREFIX + 'Configure Services')
        layout = aqt.qt.QVBoxLayout()

        # Add HyperTTS header
        header_layout = aqt.qt.QHBoxLayout()
        header_layout.addStretch()
        header_layout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        layout.addLayout(header_layout)
        
        # Add explanation label at top
        explanation = aqt.qt.QLabel("Configure HyperTTS services")
        explanation.setWordWrap(True)
        explanation.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignLeft)
        explanation.setStyleSheet('border: none; background-color: transparent;')
        font = explanation.font()
        font.setPointSize(14)
        explanation.setFont(font)
        layout.addWidget(explanation)
        
        # Add smaller description text
        description = aqt.qt.QLabel("In order to generate audio using HyperTTS, you need to enable TTS services. Choose from one of the options below.")
        description.setWordWrap(True)
        description.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignCenter)
        desc_font = description.font()
        desc_font.setPointSize(desc_font.pointSize() - 1)
        description.setFont(desc_font)
        layout.addWidget(description)
        
        # Style for the buttons with depth and shadows
        button_style = """
            QPushButton {
                border: 1px solid #c0c0c0;
                border-radius: 8px;
                padding: 20px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f8f8f8, stop: 1 #e8e8e8);
                text-align: left;
                min-height: 80px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                margin: 2px;
            }
            QPushButton:hover {
                border: 1px solid #a0a0a0;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f0f0f0);
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
            }
            QPushButton:pressed {
                border: 1px solid #808080;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #e0e0e0, stop: 1 #d0d0d0);
                box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
                margin: 3px 1px 1px 3px;
            }
        """
        
        # Trial button with enhanced blue/purple styling
        trial_button_style = """
            QPushButton {
                border: 1px solid #5a65c7;
                border-radius: 8px;
                padding: 20px;
                background: qlineargradient(x1: 0.342, y1: 0, x2: 0.658, y2: 1,
                    stop: 0 #6975dd, stop: 1 #7355b0);
                text-align: left;
                min-height: 80px;
                color: white;
                font-weight: bold;
                box-shadow: 0 3px 6px rgba(0, 0, 0, 0.2);
                margin: 2px;
            }
            QPushButton:hover {
                border: 1px solid #4a55b7;
                background: qlineargradient(x1: 0.342, y1: 0, x2: 0.658, y2: 1,
                    stop: 0 #7985ed, stop: 1 #8365c0);
                box-shadow: 0 5px 10px rgba(0, 0, 0, 0.25);
            }
            QPushButton:pressed {
                border: 1px solid #3a45a7;
                background: qlineargradient(x1: 0.342, y1: 0, x2: 0.658, y2: 1,
                    stop: 0 #5965cd, stop: 1 #6345a0);
                box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
                margin: 3px 1px 1px 3px;
            }
        """
        
        self.trial_button = aqt.qt.QPushButton()
        self.trial_button.setStyleSheet(trial_button_style)
        self.trial_button.clicked.connect(lambda: self.choose_mode(config_models.ServicesConfigurationMode.TRIAL))
        
        trial_layout = aqt.qt.QVBoxLayout()
        trial_title = aqt.qt.QLabel('Free trial for HyperTTS Pro (recommended)')
        font = trial_title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        trial_title.setFont(font)
        trial_title.setStyleSheet('border: none; background-color: transparent; color: white;')
        
        trial_description = aqt.qt.QLabel('Get access to premium voices and features with a free trial')
        trial_description.setStyleSheet('border: none; background-color: transparent; color: rgba(255, 255, 255, 0.9);')
        
        trial_layout.addWidget(trial_title)
        trial_layout.addWidget(trial_description)
        self.trial_button.setLayout(trial_layout)
        
        # Free services button
        self.free_services_button = aqt.qt.QPushButton()
        self.free_services_button.setStyleSheet(button_style)
        self.free_services_button.clicked.connect(lambda: self.choose_mode(config_models.ServicesConfigurationMode.FREE_SERVICES))
        
        free_layout = aqt.qt.QVBoxLayout()
        free_title = aqt.qt.QLabel('Enable Free Services only')
        free_title.setFont(font)
        free_title.setStyleSheet('border: none; background-color: transparent;')
        
        free_description = aqt.qt.QLabel('Use only free text-to-speech services')
        free_description.setStyleSheet('border: none; background-color: transparent; color: palette(mid);')
        
        free_layout.addWidget(free_title)
        free_layout.addWidget(free_description)
        self.free_services_button.setLayout(free_layout)
        
        # Manual configuration button
        self.manual_button = aqt.qt.QPushButton()
        self.manual_button.setStyleSheet(button_style)
        self.manual_button.clicked.connect(lambda: self.choose_mode(config_models.ServicesConfigurationMode.MANUAL_CONFIGURATION))
        
        manual_layout = aqt.qt.QVBoxLayout()
        manual_title = aqt.qt.QLabel('Manually configure services')
        manual_title.setFont(font)
        manual_title.setStyleSheet('border: none; background-color: transparent;')
        
        manual_description = aqt.qt.QLabel('Configure services yourself with your own API keys')
        manual_description.setStyleSheet('border: none; background-color: transparent; color: palette(mid);')
        
        manual_layout.addWidget(manual_title)
        manual_layout.addWidget(manual_description)
        self.manual_button.setLayout(manual_layout)
        
        # Add buttons to main layout
        layout.addWidget(self.trial_button)
        layout.addWidget(self.free_services_button)
        layout.addWidget(self.manual_button)
        
        # Cancel button
        self.cancel_button = aqt.qt.QPushButton('Cancel')
        self.cancel_button.clicked.connect(self.reject)
        
        layout.addStretch()
        layout.addWidget(self.cancel_button, alignment=aqt.qt.Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def choose_mode(self, mode):
        logger.debug(f'User selected mode: {mode}')
        self.chosen_mode = mode
        self.accept()

@sc.event(Event.open)
def show_services_configuration_dialog(hypertts) -> config_models.ServicesConfigurationMode:
    """Show dialog to choose how to configure services
    Returns:
        ServicesConfigurationMode enum value, or None if user cancelled
    """
    dialog = ServicesConfigurationDialog(hypertts)
    hypertts.anki_utils.wait_for_dialog_input(dialog, constants.DIALOG_ID_SERVICES_CONFIGURATION)
    return dialog.chosen_mode
