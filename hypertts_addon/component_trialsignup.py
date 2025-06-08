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
        self.email = None

    def get_model(self):
        return self.model

    def load_model(self, model: config_models.TrialRequestReponse):
        self.model = model

    def report_model_change(self):
        self.model_change_callback(self.get_model())

    def draw(self, global_vlayout):
        # Create stacked widget to switch between signup and verification screens
        self.stacked_widget = aqt.qt.QStackedWidget()
        
        # Create signup screen
        self.signup_widget = self.create_signup_screen()
        self.stacked_widget.addWidget(self.signup_widget)
        
        # Create verification screen
        self.verification_widget = self.create_verification_screen()
        self.stacked_widget.addWidget(self.verification_widget)
        
        # Start with signup screen
        self.stacked_widget.setCurrentIndex(0)
        
        global_vlayout.addWidget(self.stacked_widget)

    def create_signup_screen(self):
        signup_widget = aqt.qt.QWidget()
        vlayout = aqt.qt.QVBoxLayout()
        
        # Add title label
        title_label = aqt.qt.QLabel("Sign up for HyperTTS Pro Trial")
        title_label.setWordWrap(True)
        title_label.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignLeft)
        title_label.setStyleSheet('border: none; background-color: transparent;')
        font = title_label.font()
        font.setPointSize(14)
        title_label.setFont(font)
        vlayout.addWidget(title_label)
        
        # Description label
        description_label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO_TRIAL_ENTER_EMAIL)
        description_label.setWordWrap(True)
        vlayout.addWidget(description_label)
        
        # Create groupbox for the form
        groupbox = aqt.qt.QGroupBox()
        form_layout = aqt.qt.QVBoxLayout()
        
        # Email input
        email_label = aqt.qt.QLabel("<b>Email:</b>")
        form_layout.addWidget(email_label)
        self.trial_email_input = aqt.qt.QLineEdit()
        self.trial_email_input.setPlaceholderText("Enter your email (no disposable email addresses)")
        form_layout.addWidget(self.trial_email_input)
        
        # Password input
        password_label = aqt.qt.QLabel("<b>Password:</b>")
        form_layout.addWidget(password_label)
        self.trial_password_input = aqt.qt.QLineEdit()
        self.trial_password_input.setPlaceholderText("Choose a password")
        self.trial_password_input.setEchoMode(aqt.qt.QLineEdit.EchoMode.Password)
        form_layout.addWidget(self.trial_password_input)
        
        # Validation label for showing results/errors
        self.trial_validation_label = aqt.qt.QLabel()
        self.trial_validation_label.setWordWrap(True)
        form_layout.addWidget(self.trial_validation_label)
        
        # Button
        self.signup_button = aqt.qt.QPushButton('Sign Up for Trial')
        purple_gradient_style = """
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #6975dd, stop: 1 #7355b0);
                border: none;
                border-radius: 4px;
                color: white;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #7985ed, stop: 1 #8365c0);
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #5965cd, stop: 1 #6345a0);
            }
            QPushButton:disabled {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #9999aa, stop: 1 #888899);
            }
        """
        self.signup_button.setStyleSheet(purple_gradient_style)
        self.signup_button.setMinimumHeight(50)
        self.signup_button.setMinimumWidth(200)
        font_large = aqt.qt.QFont()
        font_large.setBold(True)
        font_large.setPointSize(12)
        self.signup_button.setFont(font_large)
        
        form_layout.addWidget(self.signup_button, alignment=aqt.qt.Qt.AlignmentFlag.AlignCenter)
        
        groupbox.setLayout(form_layout)
        vlayout.addWidget(groupbox)
        vlayout.addStretch()
        
        # Wire events
        self.signup_button.pressed.connect(self.signup_button_pressed)
        
        signup_widget.setLayout(vlayout)
        return signup_widget

    def create_verification_screen(self):
        verification_widget = aqt.qt.QWidget()
        vlayout = aqt.qt.QVBoxLayout()
        
        # Title label
        title_label = aqt.qt.QLabel("Email Verification Required")
        title_label.setWordWrap(True)
        title_label.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignLeft)
        title_label.setStyleSheet('border: none; background-color: transparent;')
        font = title_label.font()
        font.setPointSize(14)
        title_label.setFont(font)
        vlayout.addWidget(title_label)
        
        # Create groupbox for the verification content
        groupbox = aqt.qt.QGroupBox()
        form_layout = aqt.qt.QVBoxLayout()
        
        # Description label
        self.verification_description_label = aqt.qt.QLabel()
        self.verification_description_label.setWordWrap(True)
        form_layout.addWidget(self.verification_description_label)
        
        # Status label
        self.verification_status_label = aqt.qt.QLabel()
        self.verification_status_label.setWordWrap(True)
        form_layout.addWidget(self.verification_status_label)
        
        # Check status button
        self.check_status_button = aqt.qt.QPushButton('Check Status')
        self.check_status_button.setMinimumHeight(40)
        self.check_status_button.setMinimumWidth(150)
        form_layout.addWidget(self.check_status_button, alignment=aqt.qt.Qt.AlignmentFlag.AlignCenter)
        
        groupbox.setLayout(form_layout)
        vlayout.addWidget(groupbox)
        vlayout.addStretch()
        
        # Wire events
        self.check_status_button.pressed.connect(self.check_status_button_pressed)
        
        verification_widget.setLayout(vlayout)
        return verification_widget

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
            # Save the API key to configuration
            self.hypertts.save_hypertts_pro_api_key(trial_signup_result.api_key)
            # Switch to verification screen
            self.show_verification_screen()
        
        self.model = trial_signup_result
        self.report_model_change()

    def show_verification_screen(self):
        """Switch to the email verification screen"""
        self.verification_description_label.setText(
            f'<b>Success!</b> Trial account created for {self.email}.<br><br>'
            'Please check your email for a verification link. You must verify your email '
            'before you can use HyperTTS Pro services.'
        )
        self.verification_status_label.setText('')
        self.stacked_widget.setCurrentIndex(1)

    @sc.event(Event.click_free_trial_ok)
    def check_status_button_pressed(self):
        self.verification_status_label.setText('Checking verification status...')
        self.check_status_button.setEnabled(False)
        
        self.hypertts.anki_utils.run_in_background(self.check_verification_task, self.check_verification_task_done)

    def check_verification_task(self):
        return self.hypertts.service_manager.cloudlanguagetools.check_email_verification_status(self.email)

    def check_verification_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Checking email verification status'):
            verification_status = result.result()
            logger.debug(f'verification_status: {verification_status}')
            self.hypertts.anki_utils.run_on_main(lambda: self.check_verification_update(verification_status))

    def check_verification_update(self, verification_status: bool):
        logger.info(f'verification_status: {verification_status}')
        self.check_status_button.setEnabled(True)
        
        if verification_status:
            self.verification_status_label.setText('<b>Email verified!</b> You can now use HyperTTS Pro services.')
        else:
            self.verification_status_label.setText('Email not yet verified. Please check your email and click the verification link.')


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

        # Cancel button
        self.close_button = aqt.qt.QPushButton('Cancel')
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
