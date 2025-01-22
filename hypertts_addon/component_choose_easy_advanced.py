import aqt.qt
from . import config_models

class ChooseEasyAdvancedDialog(aqt.qt.QDialog):
    def __init__(self):
        super(aqt.qt.QDialog, self).__init__()
        self.setupUi()
        self.mode = None

    def setupUi(self):
        self.setWindowTitle('Choose Mode')
        layout = aqt.qt.QVBoxLayout()

        # Radio buttons
        self.easy_radio = aqt.qt.QRadioButton('Easy Mode')
        self.easy_radio.setChecked(True)
        self.advanced_radio = aqt.qt.QRadioButton('Advanced Mode')

        # Description labels
        easy_description = aqt.qt.QLabel('Simple interface for basic text-to-speech needs')
        advanced_description = aqt.qt.QLabel('Full control over all text-to-speech settings')

        # Button box
        button_box = aqt.qt.QDialogButtonBox(
            aqt.qt.QDialogButtonBox.Ok | aqt.qt.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Layout
        layout.addWidget(self.easy_radio)
        layout.addWidget(easy_description)
        layout.addSpacing(10)
        layout.addWidget(self.advanced_radio)
        layout.addWidget(advanced_description)
        layout.addSpacing(20)
        layout.addWidget(button_box)

        self.setLayout(layout)

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
    if dialog.exec_():
        return dialog.mode
    return None
