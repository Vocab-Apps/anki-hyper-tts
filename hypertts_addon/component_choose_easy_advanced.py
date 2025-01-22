import aqt.qt
from . import config_models

class ChooseEasyAdvancedDialog(aqt.qt.QDialog):
    """Dialog for choosing between Easy and Advanced modes"""
    def __init__(self):
        super(aqt.qt.QDialog, self).__init__()
        self.setupUi()
        self.mode = None

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
        
        easy_description = aqt.qt.QLabel('Simple interface for basic\ntext-to-speech needs')
        easy_description.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignCenter)
        
        easy_layout.addWidget(self.easy_radio, alignment=aqt.qt.Qt.AlignmentFlag.AlignCenter)
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
        
        advanced_description = aqt.qt.QLabel('Full control over all\ntext-to-speech settings')
        advanced_description.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignCenter)
        
        advanced_layout.addWidget(self.advanced_radio, alignment=aqt.qt.Qt.AlignmentFlag.AlignCenter)
        advanced_layout.addWidget(advanced_description)
        self.advanced_frame.setLayout(advanced_layout)
        
        # Add frames to horizontal layout
        options_layout.addWidget(self.easy_frame)
        options_layout.addWidget(self.advanced_frame)
        
        # Set the style sheet
        self.setStyleSheet(frame_style)
        
        # Button box
        button_box = aqt.qt.QDialogButtonBox(
            aqt.qt.QDialogButtonBox.StandardButton.Ok | 
            aqt.qt.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Main layout
        layout.addLayout(options_layout)
        layout.addSpacing(20)
        layout.addWidget(button_box)

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
        if self.easy_radio.isChecked():
            self.mode = config_models.EasyAdvancedMode.EASY
        else:
            self.mode = config_models.EasyAdvancedMode.ADVANCED
        super().accept()

def show_easy_advanced_dialog() -> config_models.EasyAdvancedMode:
    """Show dialog to choose between Easy and Advanced modes
    Returns:
        EasyAdvancedMode enum value, or None if user cancelled
    """
    dialog = ChooseEasyAdvancedDialog()
    if dialog.exec():
        return dialog.mode
    return None
