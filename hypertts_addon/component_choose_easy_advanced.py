import aqt.qt
from . import config_models
from . import constants
from . import logging_utils
from . import constants_events
from .constants_events import Event, EventMode
from . import stats

logger = logging_utils.get_test_child_logger(__name__)

sc = stats.StatsContext(constants_events.EventContext.choose_easy_advanced)

class ChooseEasyAdvancedDialog(aqt.qt.QDialog):
    """Dialog for choosing between Easy and Advanced modes"""
    def __init__(self):
        super(aqt.qt.QDialog, self).__init__()
        self.setupUi()
        self.chosen_mode = None

    def setupUi(self):
        self.setWindowTitle(constants.TITLE_PREFIX + 'Choose Mode')
        layout = aqt.qt.QVBoxLayout()

        # Add explanation label at top
        explanation = aqt.qt.QLabel(constants.GUI_TEXT_CHOICE_EASY_ADVANCED_EXPLANATION)
        explanation.setWordWrap(True)
        explanation.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignCenter)
        explanation.setStyleSheet('border: none; background-color: transparent;')
        font = explanation.font()
        font.setPointSize(14)
        explanation.setFont(font)
        layout.addWidget(explanation)
        
        # Create horizontal layout for options
        options_layout = aqt.qt.QHBoxLayout()
        
        # Style for the frames
        frame_style = """
            QFrame {
                border: 2px solid palette(mid);
                border-radius: 5px;
                padding: 10px;
                background-color: palette(window);
            }
            QFrame[selected="true"] {
                border-color: palette(highlight);
                background-color: palette(highlight);
                background-color: rgba(palette(highlight), 0.1);
            }
        """
        
        # Easy mode frame
        self.easy_frame = aqt.qt.QFrame()
        self.easy_frame.setProperty('selected', True)
        easy_layout = aqt.qt.QVBoxLayout()
        
        # Create button group for mutual exclusion
        self.button_group = aqt.qt.QButtonGroup(self)
        
        # Radio buttons with larger font
        self.easy_radio = aqt.qt.QRadioButton('Easy Mode')
        font = self.easy_radio.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        self.easy_radio.setFont(font)
        self.easy_radio.setChecked(True)
        self.button_group.addButton(self.easy_radio)
        self.easy_radio.toggled.connect(self.update_selection)
        
        easy_description = aqt.qt.QLabel(constants.GUI_TEXT_CHOICE_EASY_MODE)
        easy_description.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignCenter)
        easy_description.setWordWrap(True)
        easy_description.setStyleSheet('border: none; background-color: transparent;')
        
        easy_layout.addWidget(self.easy_radio, alignment=aqt.qt.Qt.AlignmentFlag.AlignTop | aqt.qt.Qt.AlignmentFlag.AlignHCenter)
        easy_layout.addWidget(easy_description, alignment=aqt.qt.Qt.AlignmentFlag.AlignTop)
        easy_layout.addStretch()
        self.easy_frame.setLayout(easy_layout)
        
        # Advanced mode frame
        self.advanced_frame = aqt.qt.QFrame()
        self.advanced_frame.setProperty('selected', False)
        advanced_layout = aqt.qt.QVBoxLayout()
        
        self.advanced_radio = aqt.qt.QRadioButton('Advanced Mode')
        self.advanced_radio.setFont(font)
        self.button_group.addButton(self.advanced_radio)
        self.advanced_radio.toggled.connect(self.update_selection)
        
        advanced_description = aqt.qt.QLabel(constants.GUI_TEXT_CHOICE_ADVANCED_MODE)
        advanced_description.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignCenter)
        advanced_description.setWordWrap(True)
        advanced_description.setStyleSheet('border: none; background-color: transparent;')
        
        advanced_layout.addWidget(self.advanced_radio, alignment=aqt.qt.Qt.AlignmentFlag.AlignTop | aqt.qt.Qt.AlignmentFlag.AlignHCenter)
        advanced_layout.addWidget(advanced_description, alignment=aqt.qt.Qt.AlignmentFlag.AlignTop)
        advanced_layout.addStretch()
        self.advanced_frame.setLayout(advanced_layout)
        
        # Add frames to horizontal layout
        options_layout.addWidget(self.easy_frame)
        options_layout.addWidget(self.advanced_frame)
        
        # Set the style sheet
        self.setStyleSheet(frame_style)
        
        # Button box
        self.button_box = aqt.qt.QDialogButtonBox(
            aqt.qt.QDialogButtonBox.StandardButton.Ok | 
            aqt.qt.QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Main layout
        layout.addLayout(options_layout)
        
        explanation_bottom = aqt.qt.QLabel(constants.GUI_TEXT_CHOICE_EASY_ADVANCED_BOTTOM)
        explanation_bottom.setWordWrap(True)
        explanation_bottom.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignCenter)
        explanation_bottom.setStyleSheet('border: none; background-color: transparent;')
        layout.addWidget(explanation_bottom)

        layout.addStretch()
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def update_selection(self):
        self.easy_frame.setProperty('selected', self.easy_radio.isChecked())
        self.advanced_frame.setProperty('selected', self.advanced_radio.isChecked())
        
        # Force style refresh
        self.easy_frame.style().unpolish(self.easy_frame)
        self.easy_frame.style().polish(self.easy_frame)
        self.advanced_frame.style().unpolish(self.advanced_frame)
        self.advanced_frame.style().polish(self.advanced_frame)

    def accept(self):
        logger.debug('accept')
        if self.easy_radio.isChecked():
            self.chosen_mode = config_models.EasyAdvancedMode.EASY
        else:
            self.chosen_mode = config_models.EasyAdvancedMode.ADVANCED
        logger.debug(f'User selected mode: {self.chosen_mode}')
        super().accept()

@sc.event(Event.open)
def show_easy_advanced_dialog(hypertts) -> config_models.EasyAdvancedMode:
    """Show dialog to choose between Easy and Advanced modes
    Returns:
        EasyAdvancedMode enum value, or None if user cancelled
    """
    dialog = ChooseEasyAdvancedDialog()
    hypertts.anki_utils.wait_for_dialog_input(dialog, constants.DIALOG_ID_CHDOOSE_EASY_ADVANCED)
    return dialog.chosen_mode

def ensure_easy_advanced_choice_made(hypertts) -> bool:
    """Ensure user has made a choice between Easy and Advanced modes.
    If not, show the dialog and save their choice."""

    # return True if we can proceed to the next step    

    configuration = hypertts.get_configuration()
    if configuration.user_choice_easy_advanced:
        return True  # can proceed to the next step

    logger.debug('user hasnt chosen easy/advanced mode yet')
    # User hasn't chosen yet, show dialog
    choice = show_easy_advanced_dialog(hypertts)
    if choice is not None:
        # Save their choice
        configuration.user_choice_easy_advanced = True
        hypertts.save_configuration(configuration)
        
        # Update mapping rules based on their choice
        mapping_rules = hypertts.load_mapping_rules()
        mapping_rules.use_easy_mode = (choice == config_models.EasyAdvancedMode.EASY)
        hypertts.save_mapping_rules(mapping_rules)

        if mapping_rules.use_easy_mode:
            sc.send_event(Event.choose, EventMode.easy_mode)
        else:
            sc.send_event(Event.choose, EventMode.advanced_mode)
        
        return True
                
    return False