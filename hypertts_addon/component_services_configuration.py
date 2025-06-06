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
        self.setMinimumWidth(500)
        layout = aqt.qt.QVBoxLayout()

        # Add HyperTTS header
        header_layout = aqt.qt.QHBoxLayout()
        header_layout.addStretch()
        header_layout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        layout.addLayout(header_layout)
        
        # Add explanation label at top
        explanation = aqt.qt.QLabel(constants.GUI_TEXT_SERVICES_CONFIG_TITLE)
        explanation.setWordWrap(True)
        explanation.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignLeft)
        explanation.setStyleSheet('border: none; background-color: transparent;')
        font = explanation.font()
        font.setPointSize(14)
        explanation.setFont(font)
        layout.addWidget(explanation)
        
        # Add smaller description text
        description = aqt.qt.QLabel(constants.GUI_TEXT_SERVICES_CONFIG_DESCRIPTION)
        description.setWordWrap(True)
        description.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignCenter)
        description.setStyleSheet('border: none; background-color: transparent; color: palette(dark);')
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
        
        # Trial button with purple outline and structured layout
        trial_button_style = """
            QPushButton {
                border: 3px solid #6975dd;
                border-radius: 8px;
                padding: 0px;
                background: #f8f8f8;
                text-align: left;
                min-height: 150px;
                box-shadow: 0 3px 6px rgba(0, 0, 0, 0.2);
                margin: 2px;
            }
            QPushButton:hover {
                border: 3px solid #7985ed;
                background: #ffffff;
                box-shadow: 0 5px 10px rgba(0, 0, 0, 0.25);
            }
            QPushButton:pressed {
                border: 3px solid #5965cd;
                background: #f0f0f0;
                box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
                margin: 3px 1px 1px 3px;
            }
        """
        
        self.trial_button = aqt.qt.QPushButton()
        self.trial_button.setStyleSheet(trial_button_style)
        self.trial_button.clicked.connect(lambda: self.choose_mode(config_models.ServicesConfigurationMode.TRIAL))
        
        trial_layout = aqt.qt.QVBoxLayout()
        trial_layout.setContentsMargins(0, 0, 0, 0)
        trial_layout.setSpacing(0)
        
        # Header with gradient background
        trial_header = aqt.qt.QWidget()
        trial_header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1: 0.342, y1: 0, x2: 0.658, y2: 1,
                    stop: 0 #6975dd, stop: 1 #7355b0);
                border-radius: 5px 5px 0px 0px;
            }
        """)
        trial_header_layout = aqt.qt.QVBoxLayout()
        trial_header_layout.setContentsMargins(15, 10, 15, 10)
        
        trial_title = aqt.qt.QLabel(constants.GUI_TEXT_SERVICES_CONFIG_TRIAL_TITLE)
        font = trial_title.font()
        font.setPointSize(font.pointSize() + 4)
        trial_title.setFont(font)
        trial_title.setStyleSheet('border: none; background-color: transparent; color: white;')
        trial_header_layout.addWidget(trial_title)
        trial_header.setLayout(trial_header_layout)
        
        # Body with light gray background
        trial_body = aqt.qt.QWidget()
        trial_body.setStyleSheet("""
            QWidget {
                background: #f8f8f8;
                border-radius: 0px 0px 5px 5px;
            }
        """)
        trial_body_layout = aqt.qt.QVBoxLayout()
        trial_body_layout.setContentsMargins(15, 10, 15, 15)
        trial_body_layout.setSpacing(8)
        
        trial_description = aqt.qt.QLabel(constants.GUI_TEXT_SERVICES_CONFIG_TRIAL_DESCRIPTION)
        trial_description.setWordWrap(True)
        trial_description.setStyleSheet('border: none; background-color: transparent; color: #333333;')
        trial_description.setSizePolicy(aqt.qt.QSizePolicy.Policy.Expanding, aqt.qt.QSizePolicy.Policy.Expanding)
        
        trial_recommended = aqt.qt.QLabel(constants.GUI_TEXT_SERVICES_CONFIG_TRIAL_RECOMMENDED)
        trial_recommended.setStyleSheet('border: none; background-color: transparent; color: #666666; font-style: italic;')
        trial_recommended.setSizePolicy(aqt.qt.QSizePolicy.Policy.Expanding, aqt.qt.QSizePolicy.Policy.Minimum)
        
        trial_body_layout.addWidget(trial_description)
        trial_body_layout.addWidget(trial_recommended)
        trial_body.setLayout(trial_body_layout)
        
        trial_layout.addWidget(trial_header)
        trial_layout.addWidget(trial_body)
        self.trial_button.setLayout(trial_layout)
        
        # Free services button
        self.free_services_button = aqt.qt.QPushButton()
        self.free_services_button.setStyleSheet(button_style)
        self.free_services_button.clicked.connect(lambda: self.choose_mode(config_models.ServicesConfigurationMode.FREE_SERVICES))
        
        free_layout = aqt.qt.QVBoxLayout()
        free_layout.setContentsMargins(0, 0, 0, 0)
        free_layout.setSpacing(0)
        
        # Header with gradient background
        free_header = aqt.qt.QWidget()
        free_header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f8f8f8, stop: 1 #e8e8e8);
                border-radius: 5px 5px 0px 0px;
            }
        """)
        free_header_layout = aqt.qt.QVBoxLayout()
        free_header_layout.setContentsMargins(15, 10, 15, 10)
        
        free_title = aqt.qt.QLabel(constants.GUI_TEXT_SERVICES_CONFIG_FREE_TITLE)
        free_font = free_title.font()
        free_font.setPointSize(free_font.pointSize() + 4)
        free_title.setFont(free_font)
        free_title.setStyleSheet('border: none; background-color: transparent; color: #333333;')
        free_header_layout.addWidget(free_title)
        free_header.setLayout(free_header_layout)
        
        # Body with light gray background
        free_body = aqt.qt.QWidget()
        free_body.setStyleSheet("""
            QWidget {
                background: #f8f8f8;
                border-radius: 0px 0px 5px 5px;
            }
        """)
        free_body_layout = aqt.qt.QVBoxLayout()
        free_body_layout.setContentsMargins(15, 10, 15, 15)
        
        free_description = aqt.qt.QLabel(constants.GUI_TEXT_SERVICES_CONFIG_FREE_DESCRIPTION)
        free_description.setWordWrap(True)
        free_description.setStyleSheet('border: none; background-color: transparent; color: #333333;')
        
        free_body_layout.addWidget(free_description)
        free_body.setLayout(free_body_layout)
        
        free_layout.addWidget(free_header)
        free_layout.addWidget(free_body)
        self.free_services_button.setLayout(free_layout)
        
        # Manual configuration button
        self.manual_button = aqt.qt.QPushButton()
        self.manual_button.setStyleSheet(button_style)
        self.manual_button.clicked.connect(lambda: self.choose_mode(config_models.ServicesConfigurationMode.MANUAL_CONFIGURATION))
        
        manual_layout = aqt.qt.QVBoxLayout()
        manual_layout.setContentsMargins(0, 0, 0, 0)
        manual_layout.setSpacing(0)
        
        # Header with gradient background
        manual_header = aqt.qt.QWidget()
        manual_header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f8f8f8, stop: 1 #e8e8e8);
                border-radius: 5px 5px 0px 0px;
            }
        """)
        manual_header_layout = aqt.qt.QVBoxLayout()
        manual_header_layout.setContentsMargins(15, 10, 15, 10)
        
        manual_title = aqt.qt.QLabel(constants.GUI_TEXT_SERVICES_CONFIG_MANUAL_TITLE)
        manual_font = manual_title.font()
        manual_font.setPointSize(manual_font.pointSize() + 4)
        manual_title.setFont(manual_font)
        manual_title.setStyleSheet('border: none; background-color: transparent; color: #333333;')
        manual_header_layout.addWidget(manual_title)
        manual_header.setLayout(manual_header_layout)
        
        # Body with light gray background
        manual_body = aqt.qt.QWidget()
        manual_body.setStyleSheet("""
            QWidget {
                background: #f8f8f8;
                border-radius: 0px 0px 5px 5px;
            }
        """)
        manual_body_layout = aqt.qt.QVBoxLayout()
        manual_body_layout.setContentsMargins(15, 10, 15, 15)
        
        manual_description = aqt.qt.QLabel(constants.GUI_TEXT_SERVICES_CONFIG_MANUAL_DESCRIPTION)
        manual_description.setWordWrap(True)
        manual_description.setStyleSheet('border: none; background-color: transparent; color: #333333;')
        
        manual_body_layout.addWidget(manual_description)
        manual_body.setLayout(manual_body_layout)
        
        manual_layout.addWidget(manual_header)
        manual_layout.addWidget(manual_body)
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
