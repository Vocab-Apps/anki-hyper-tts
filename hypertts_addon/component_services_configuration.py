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
        
        # Trial button with purple outline and HTML content
        trial_button_style = """
            QLabel {
                border: 3px solid #6975dd;
                border-radius: 8px;
                padding: 0px;
                background: #ffffff;
                min-height: 160px;
                margin: 2px;
            }
            QLabel:hover {
                border: 3px solid #7985ed;
                background: #f8f8f8;
            }
        """
        
        trial_html = f"""
        <div style="background: linear-gradient(39deg, #6975dd, #7355b0); padding: 15px; border-radius: 5px 5px 0px 0px;">
            <h3 style="color: white; margin: 0; font-size: 16px; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">{constants.GUI_TEXT_SERVICES_CONFIG_TRIAL_TITLE}</h3>
        </div>
        <div style="background: #f8f8f8; padding: 15px; border-radius: 0px 0px 5px 5px;">
            <p style="color: #333333; margin: 0 0 10px 0;">{constants.GUI_TEXT_SERVICES_CONFIG_TRIAL_DESCRIPTION}</p>
            <p style="color: #666666; margin: 0; font-style: italic;">{constants.GUI_TEXT_SERVICES_CONFIG_TRIAL_RECOMMENDED}</p>
        </div>
        """
        
        self.trial_button = aqt.qt.QLabel()
        self.trial_button.setStyleSheet(trial_button_style)
        self.trial_button.setText(trial_html)
        self.trial_button.setWordWrap(True)
        self.trial_button.mousePressEvent = lambda event: self.choose_mode(config_models.ServicesConfigurationMode.TRIAL)
        
        # Free services button with grey outline and HTML content
        free_button_style = """
            QLabel {
                border: 3px solid #c0c0c0;
                border-radius: 8px;
                padding: 0px;
                background: #ffffff;
                min-height: 140px;
                margin: 2px;
            }
            QLabel:hover {
                border: 3px solid #a0a0a0;
                background: #f8f8f8;
            }
        """
        
        free_html = f"""
        <div style="background: linear-gradient(0deg, #f8f8f8, #e8e8e8); padding: 15px; border-radius: 5px 5px 0px 0px;">
            <h3 style="color: #333333; margin: 0; font-size: 16px;">{constants.GUI_TEXT_SERVICES_CONFIG_FREE_TITLE}</h3>
        </div>
        <div style="background: #f8f8f8; padding: 15px; border-radius: 0px 0px 5px 5px;">
            <p style="color: #333333; margin: 0 0 10px 0;">{constants.GUI_TEXT_SERVICES_CONFIG_FREE_DESCRIPTION}</p>
            <p style="color: #666666; margin: 0; font-style: italic;">{constants.GUI_TEXT_SERVICES_CONFIG_FREE_RECOMMENDED}</p>
        </div>
        """
        
        self.free_services_button = aqt.qt.QLabel()
        self.free_services_button.setStyleSheet(free_button_style)
        self.free_services_button.setText(free_html)
        self.free_services_button.setWordWrap(True)
        self.free_services_button.mousePressEvent = lambda event: self.choose_mode(config_models.ServicesConfigurationMode.FREE_SERVICES)
        
        # Manual configuration button with grey outline and HTML content
        manual_button_style = """
            QLabel {
                border: 3px solid #c0c0c0;
                border-radius: 8px;
                padding: 0px;
                background: #ffffff;
                min-height: 140px;
                margin: 2px;
            }
            QLabel:hover {
                border: 3px solid #a0a0a0;
                background: #f8f8f8;
            }
        """
        
        manual_html = f"""
        <div style="background: linear-gradient(0deg, #f8f8f8, #e8e8e8); padding: 15px; border-radius: 5px 5px 0px 0px;">
            <h3 style="color: #333333; margin: 0; font-size: 16px;">{constants.GUI_TEXT_SERVICES_CONFIG_MANUAL_TITLE}</h3>
        </div>
        <div style="background: #f8f8f8; padding: 15px; border-radius: 0px 0px 5px 5px;">
            <p style="color: #333333; margin: 0 0 10px 0;">{constants.GUI_TEXT_SERVICES_CONFIG_MANUAL_DESCRIPTION}</p>
            <p style="color: #666666; margin: 0; font-style: italic;">{constants.GUI_TEXT_SERVICES_CONFIG_MANUAL_RECOMMENDED}</p>
        </div>
        """
        
        self.manual_button = aqt.qt.QLabel()
        self.manual_button.setStyleSheet(manual_button_style)
        self.manual_button.setText(manual_html)
        self.manual_button.setWordWrap(True)
        self.manual_button.mousePressEvent = lambda event: self.choose_mode(config_models.ServicesConfigurationMode.MANUAL_CONFIGURATION)
        
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
