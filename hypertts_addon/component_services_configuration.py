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
        description.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignLeft)
        description.setStyleSheet('border: none; background-color: transparent; color: palette(dark);')
        desc_font = description.font()
        desc_font.setPointSize(desc_font.pointSize() - 1)
        description.setFont(desc_font)
        layout.addWidget(description)
        
       
        # Common styles
        border_width = "2px"
        
        common_button_style = """
            QLabel {
                border-radius: 8px;
                padding: 0px;
                padding-left: 15px;
                padding-right: 15px;
                background: #e8e8e8;
                min-height: 160px;
                margin: 2px;
            }
            h3 {
                font-size: 18px;
            }
"""

        # Trial button with purple gradient background and white text
        trial_button_style = common_button_style + f"""
            QLabel {{
                border: {border_width} solid {constants.COLOR_GRADIENT_PURPLE_START};
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {constants.COLOR_GRADIENT_PURPLE_START}, stop: 1 {constants.COLOR_GRADIENT_PURPLE_END});
                color: white;
            }}
            QLabel:hover {{
                border: {border_width} solid {constants.COLOR_GRADIENT_PURPLE_END};
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {constants.COLOR_GRADIENT_PURPLE_HOVER_START}, stop: 1 {constants.COLOR_GRADIENT_PURPLE_HOVER_END});
            }}
        """
        
        trial_html = f"""
        <div>
            <h3>{constants.GUI_TEXT_SERVICES_CONFIG_TRIAL_TITLE}</h3>
        </div>
        <div>
            <p>{constants.GUI_TEXT_SERVICES_CONFIG_TRIAL_DESCRIPTION}</p>
            <p><i>{constants.GUI_TEXT_SERVICES_CONFIG_TRIAL_RECOMMENDED}</i></p>
        </div>
        """
        
        self.trial_button = aqt.qt.QLabel()
        self.trial_button.setStyleSheet(trial_button_style)
        self.trial_button.setText(trial_html)
        self.trial_button.setWordWrap(True)
        self.trial_button.mousePressEvent = lambda event: self.choose_mode(config_models.ServicesConfigurationMode.TRIAL)
        
        # Manual configuration button with grey outline and HTML content
        manual_button_style = common_button_style + f"""
            QLabel {{
                border: {border_width} solid palette(mid);
                background: palette(button);
                color: palette(button-text);
            }}
            QLabel:hover {{
                border: {border_width} solid {constants.COLOR_GRADIENT_PURPLE_END};
                background: palette(alternate-base);
                color: palette(text);
            }}
        """
        
        manual_html = f"""
        <div>
            <h3>{constants.GUI_TEXT_SERVICES_CONFIG_MANUAL_TITLE}</h3>
        </div>
        <div>
            <p>{constants.GUI_TEXT_SERVICES_CONFIG_MANUAL_DESCRIPTION}</p>
            <p><i>{constants.GUI_TEXT_SERVICES_CONFIG_MANUAL_RECOMMENDED}</i></p>
        </div>
        """
        
        self.manual_button = aqt.qt.QLabel()
        self.manual_button.setStyleSheet(manual_button_style)
        self.manual_button.setText(manual_html)
        self.manual_button.setWordWrap(True)
        self.manual_button.mousePressEvent = lambda event: self.choose_mode(config_models.ServicesConfigurationMode.MANUAL_CONFIGURATION)
        
        # Add buttons to main layout
        layout.addWidget(self.trial_button)
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
