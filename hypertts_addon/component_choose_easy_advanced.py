import aqt.qt
from . import config_models
from . import constants
from . import logging_utils

logger = logging_utils.get_test_child_logger(__name__)

class ChooseEasyAdvancedDialog(aqt.qt.QDialog):
    """Dialog for choosing between Easy and Advanced modes"""
    def __init__(self):
        super(aqt.qt.QDialog, self).__init__()
        self.setupUi()
        self.chosen_mode = None

    def setupUi(self):
        self.setWindowTitle('Choose Mode')
        layout = aqt.qt.QVBoxLayout()
        
        # Create horizontal layout for options
        options_layout = aqt.qt.QHBoxLayout()
        
        # Style for the frames
        frame_style = """
            QFrame {
                border: 2px solid #ccc;
                border-radius: 5px;
                padding: 10px;
                background-color: #f0f0f0;
            }
            QFrame[selected="true"] {
                border-color: #2196F3;
                background-color: #E3F2FD;
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
        easy_layout.addWidget(easy_description)
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
        advanced_layout.addWidget(advanced_description)
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
        layout.addSpacing(20)
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

def show_easy_advanced_dialog(hypertts) -> config_models.EasyAdvancedMode:
    """Show dialog to choose between Easy and Advanced modes
    Returns:
        EasyAdvancedMode enum value, or None if user cancelled
    """
    dialog = ChooseEasyAdvancedDialog()
    hypertts.anki_utils.wait_for_dialog_input(dialog, constants.DIALOG_ID_CHDOOSE_EASY_ADVANCED)
    return dialog.chosen_mode

def ensure_easy_advanced_choice_made(hypertts):
    """Ensure user has made a choice between Easy and Advanced modes.
    If not, show the dialog and save their choice."""
    
    configuration = hypertts.get_configuration()
    if not configuration.user_choice_easy_advanced:
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
