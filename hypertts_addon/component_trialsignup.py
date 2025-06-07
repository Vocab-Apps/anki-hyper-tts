import sys
import aqt.qt
import pprint

from . import component_common
from . import constants
from . import constants_events
from .constants_events import Event
from . import logging_utils
from . import gui_utils
from . import config_models
from . import stats

logger = logging_utils.get_child_logger(__name__)

sc = stats.StatsContext(constants_events.EventContext.hyperttspro)

class TrialSignup(component_common.ConfigComponentBase):
    def __init__(self, hypertts, model_change_callback):
        self.hypertts = hypertts
        self.model_change_callback = model_change_callback
        self.model = config_models.TrialRequestReponse(success=False, error=None, api_key=None)

    def get_model(self):
        return self.model

    def load_model(self, model: config_models.TrialRequestReponse):
        self.model = model

    def report_model_change(self):
        self.model_change_callback(self.get_model())

    def draw(self, global_vlayout):
        groupbox = aqt.qt.QGroupBox('HyperTTS Pro Trial Signup')
        
        vlayout = aqt.qt.QVBoxLayout()
        
        # Description label
        description_label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO_TRIAL_ENTER_EMAIL)
        description_label.setWordWrap(True)
        vlayout.addWidget(description_label)
        
        # Email input
        email_label = aqt.qt.QLabel("Email:")
        vlayout.addWidget(email_label)
        self.trial_email_input = aqt.qt.QLineEdit()
        self.trial_email_input.setPlaceholderText("Enter your email (no disposable email addresses)")
        vlayout.addWidget(self.trial_email_input)
        
        # Password input
        password_label = aqt.qt.QLabel("Password:")
        vlayout.addWidget(password_label)
        self.trial_password_input = aqt.qt.QLineEdit()
        self.trial_password_input.setPlaceholderText("Choose a password")
        self.trial_password_input.setEchoMode(aqt.qt.QLineEdit.EchoMode.Password)
        vlayout.addWidget(self.trial_password_input)
        
        # Validation label for showing results/errors
        self.trial_validation_label = aqt.qt.QLabel()
        self.trial_validation_label.setWordWrap(True)
        vlayout.addWidget(self.trial_validation_label)
        
        # Buttons
        button_layout = aqt.qt.QHBoxLayout()
        self.signup_button = aqt.qt.QPushButton('Sign Up for Trial')
        self.signup_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        font_large = aqt.qt.QFont()
        font_large.setBold(True)
        self.signup_button.setFont(font_large)
        button_layout.addWidget(self.signup_button)
        
        self.clear_button = aqt.qt.QPushButton('Clear')
        button_layout.addWidget(self.clear_button)
        
        vlayout.addLayout(button_layout)
        vlayout.addStretch()
        
        groupbox.setLayout(vlayout)
        
        # Wire events
        self.signup_button.pressed.connect(self.signup_button_pressed)
        self.clear_button.pressed.connect(self.clear_button_pressed)
        
        global_vlayout.addWidget(groupbox)

    @sc.event(Event.click_free_trial_ok)
    def signup_button_pressed(self):
        email = self.trial_email_input.text().strip()
        password = self.trial_password_input.text().strip()
        
        if not email:
            self.trial_validation_label.setText('<b>Error:</b> Please enter an email address')
            return
            
        if not password:
            self.trial_validation_label.setText('<b>Error:</b> Please enter a password')
            return
        
        self.trial_validation_label.setText('Signing up for trial...')
        self.signup_button.setEnabled(False)
        
        self.email = email
        self.password = password
        self.hypertts.anki_utils.run_in_background(self.trial_signup_task, self.trial_signup_task_done)

    def clear_button_pressed(self):
        self.trial_email_input.clear()
        self.trial_password_input.clear()
        self.trial_validation_label.clear()
        self.signup_button.setEnabled(True)
        self.model = config_models.TrialRequestReponse(success=False, error=None, api_key=None)
        self.report_model_change()

    def trial_signup_task(self):
        client_uuid = self.hypertts.get_client_uuid()
        return self.hypertts.service_manager.cloudlanguagetools.request_trial_key(self.email, self.password, client_uuid)

    def trial_signup_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Signing up for trial'):
            trial_signup_result = result.result()
            logger.debug(f'trial_signup_result: {trial_signup_result}')
            self.hypertts.anki_utils.run_on_main(lambda: self.trial_signup_update(trial_signup_result))

    def trial_signup_update(self, trial_signup_result: config_models.TrialRequestReponse):
        logger.info(f'trial_signup_result: {pprint.pformat(trial_signup_result)}')
        self.signup_button.setEnabled(True)
        
        if trial_signup_result.success == False:
            self.trial_validation_label.setText(trial_signup_result.error)
        else:
            self.trial_validation_label.setText('<b>Success!</b> Trial account created. Please check your email for confirmation.')
            # Show info message about email confirmation
            self.hypertts.anki_utils.info_message(constants.GUI_TEXT_HYPERTTS_PRO_TRIAL_CONFIRM_EMAIL, None)
        
        self.model = trial_signup_result
        self.report_model_change()


class TrialSignupDialog(aqt.qt.QDialog):
    """Dialog for HyperTTS Pro trial signup"""
    def __init__(self, hypertts):
        super(aqt.qt.QDialog, self).__init__()
        self.hypertts = hypertts
        self.trial_signup_component = None
        self.setupUi()

    def setupUi(self):
        self.setWindowTitle(constants.TITLE_PREFIX + 'HyperTTS Pro Trial Signup')
        self.setMinimumWidth(500)
        layout = aqt.qt.QVBoxLayout()

        # Add HyperTTS header
        header_layout = aqt.qt.QHBoxLayout()
        header_layout.addStretch()
        header_layout.addLayout(gui_utils.get_hypertts_label_header(self.hypertts.hypertts_pro_enabled()))
        layout.addLayout(header_layout)

        # Create trial signup component
        def model_change_callback(model):
            # Handle model changes if needed
            pass

        self.trial_signup_component = TrialSignup(self.hypertts, model_change_callback)
        self.trial_signup_component.draw(layout)

        # Close button
        self.close_button = aqt.qt.QPushButton('Close')
        self.close_button.clicked.connect(self.accept)
        
        layout.addStretch()
        layout.addWidget(self.close_button, alignment=aqt.qt.Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def get_trial_result(self):
        """Get the trial signup result"""
        if self.trial_signup_component:
            return self.trial_signup_component.get_model()
        return None


@sc.event(Event.open)
def show_trial_signup_dialog(hypertts) -> config_models.TrialRequestReponse:
    """Show dialog for HyperTTS Pro trial signup
    Returns:
        TrialRequestReponse with signup result, or None if user cancelled
    """
    dialog = TrialSignupDialog(hypertts)
    result = dialog.exec()
    if result == aqt.qt.QDialog.DialogCode.Accepted:
        return dialog.get_trial_result()
    return None
