import sys
import aqt.qt
import pprint
import webbrowser


from . import component_common
from . import constants
from . import constants_events
from .constants_events import Event
from . import logging_utils
from . import gui_utils
from . import config_models
from . import stats

logger = logging_utils.get_child_logger(__name__)

sc = stats.StatsContext(constants_events.EventContext.trial_signup)

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
        
        # Create verified screen
        self.verified_widget = self.create_verified_screen()
        self.stacked_widget.addWidget(self.verified_widget)
        
        # Start with signup screen
        self.stacked_widget.setCurrentIndex(0)
        
        global_vlayout.addWidget(self.stacked_widget)

    def create_signup_screen(self):
        signup_widget = aqt.qt.QWidget()
        vlayout = aqt.qt.QVBoxLayout()
        
        # Add title label
        title_label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO_TRIAL_ALTERNATE_TITLE)
        title_label.setWordWrap(True)
        title_label.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignLeft)
        title_label.setStyleSheet('border: none; background-color: transparent;')
        font = title_label.font()
        font.setPointSize(14)
        title_label.setFont(font)
        vlayout.addWidget(title_label)
        
        # Add benefits section
        benefits_label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO_TRIAL_ALTERNATE_BENEFITS)
        benefits_label.setWordWrap(True)
        benefits_label.setStyleSheet('border: none; background-color: transparent;')
        vlayout.addWidget(benefits_label)
        
        # Create groupbox for the form
        groupbox = aqt.qt.QGroupBox()
        form_layout = aqt.qt.QVBoxLayout()
        
        # Email input
        email_label = aqt.qt.QLabel("<b>Email:</b>")
        form_layout.addWidget(email_label)
        self.trial_email_input = aqt.qt.QLineEdit()
        self.trial_email_input.setPlaceholderText("Enter your email")
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
        self.signup_button = aqt.qt.QPushButton(constants.GUI_TEXT_HYPERTTS_PRO_TRIAL_ALTERNATE_BUTTON)
        gui_utils.configure_purple_button(self.signup_button)
        
        # Add less spacing before button
        form_layout.addSpacing(-5)
        
        form_layout.addWidget(self.signup_button, alignment=aqt.qt.Qt.AlignmentFlag.AlignCenter)
        
        groupbox.setLayout(form_layout)
        vlayout.addWidget(groupbox)
        
        # Add privacy text - outside the groupbox
        privacy_label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO_TRIAL_ALTERNATE_PRIVACY)
        privacy_label.setWordWrap(True)
        privacy_label.setStyleSheet('border: none; background-color: transparent;')
        vlayout.addWidget(privacy_label)
        
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
        
        # Description label
        description_label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO_TRIAL_VERIFY_EMAIL)
        description_label.setWordWrap(True)
        vlayout.addWidget(description_label)
        
        # Create groupbox for the verification content
        groupbox = aqt.qt.QGroupBox()
        form_layout = aqt.qt.QVBoxLayout()
        
        # Detailed description label
        self.verification_description_label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO_TRIAL_VERIFICATION_DESCRIPTION)
        self.verification_description_label.setWordWrap(True)
        form_layout.addWidget(self.verification_description_label)
        
        # Status label
        self.verification_status_label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO_TRIAL_VERIFICATION_INITIAL_STATUS)
        self.verification_status_label.setWordWrap(True)
        form_layout.addWidget(self.verification_status_label)
        
        # Check status button
        self.check_status_button = aqt.qt.QPushButton('Check Status')
        gui_utils.configure_purple_button(self.check_status_button, min_height=40, min_width=150)
        form_layout.addWidget(self.check_status_button, alignment=aqt.qt.Qt.AlignmentFlag.AlignCenter)
        
        groupbox.setLayout(form_layout)
        vlayout.addWidget(groupbox)
        vlayout.addStretch()
        
        # Wire events
        self.check_status_button.pressed.connect(self.check_status_button_pressed)
        
        verification_widget.setLayout(vlayout)
        return verification_widget

    def create_verified_screen(self):
        verified_widget = aqt.qt.QWidget()
        vlayout = aqt.qt.QVBoxLayout()
        
        # Title label
        title_label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO_TRIAL_VERIFIED_TITLE)
        title_label.setWordWrap(True)
        title_label.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignLeft)
        title_label.setStyleSheet('border: none; background-color: transparent;')
        font = title_label.font()
        font.setPointSize(14)
        title_label.setFont(font)
        vlayout.addWidget(title_label)
        
        # Create groupbox for the verified content
        groupbox = aqt.qt.QGroupBox()
        form_layout = aqt.qt.QVBoxLayout()
        
        # Description label
        description_label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO_TRIAL_VERIFIED_DESCRIPTION)
        description_label.setWordWrap(True)
        form_layout.addWidget(description_label)
        
        # How to Add Audio button
        self.how_to_add_audio_button = aqt.qt.QPushButton('How to Add Audio')
        gui_utils.configure_purple_button(self.how_to_add_audio_button, min_height=40, min_width=200)
        form_layout.addWidget(self.how_to_add_audio_button, alignment=aqt.qt.Qt.AlignmentFlag.AlignCenter)
        
        groupbox.setLayout(form_layout)
        vlayout.addWidget(groupbox)
        vlayout.addStretch()
        
        # Wire events
        self.how_to_add_audio_button.pressed.connect(self.how_to_add_audio_button_pressed)
        
        verified_widget.setLayout(vlayout)
        return verified_widget

    @sc.event(Event.click_trial_signup)
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
            self.trial_signup_error(trial_signup_result)
        else:
            self.trial_signup_success(trial_signup_result)
        
        self.model = trial_signup_result
        self.report_model_change()

    @sc.event(Event.trial_signup_error)
    def trial_signup_error(self, trial_signup_result: config_models.TrialRequestReponse):
        self.trial_validation_label.setText(f'<b>Error:</b> {trial_signup_result.error}')

    @sc.event(Event.trial_signup_success)
    def trial_signup_success(self, trial_signup_result: config_models.TrialRequestReponse):
        # Save the API key to configuration
        self.hypertts.save_hypertts_pro_api_key(trial_signup_result.api_key)
        # Switch to verification screen
        self.show_verification_screen()

    def show_verification_screen(self):
        """Switch to the email verification screen"""
        self.verification_status_label.setText('')
        self.stacked_widget.setCurrentIndex(1)

    @sc.event(Event.click_email_verification_status)
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
            # Switch to verified screen
            self.email_verification_success()
        else:
            self.email_verification_failure()

    @sc.event(Event.email_verification_success)
    def email_verification_success(self):
        self.show_verified_screen()

    @sc.event(Event.email_verification_failure)
    def email_verification_failure(self):
        self.verification_status_label.setText('Email not yet verified. Please check your email (including spam folder) and click the verification link.')

    def show_verified_screen(self):
        """Switch to the verified email screen"""
        self.stacked_widget.setCurrentIndex(2)

    @sc.event(Event.click_how_to_add_audio)
    def how_to_add_audio_button_pressed(self):
        """Open the How to Add Audio guide in browser"""
        user_uuid = self.hypertts.get_client_uuid()
        url = gui_utils.get_vocab_ai_url('tips/hypertts-adding-audio', 'deckbrowser_welcome', user_uuid)
        logger.info(f'opening url: {url}')
        webbrowser.open(url)


class TrialSignupDialog(aqt.qt.QDialog):
    """Dialog for HyperTTS Pro trial signup"""
    def __init__(self, hypertts):
        super(aqt.qt.QDialog, self).__init__()
        self.hypertts = hypertts
        self.trial_signup_component = None
        self.accepted_result = False
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
            if model and model.success:
                self.accepted_result = True

        self.trial_signup_component = TrialSignup(self.hypertts, model_change_callback)
        self.trial_signup_component.draw(layout)

        layout.addStretch()

        self.setLayout(layout)

    def get_trial_result(self):
        """Get the trial signup result"""
        if self.trial_signup_component and self.accepted_result:
            return self.trial_signup_component.get_model()
        return None
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        if not self.accepted_result:
            sc.send_event(Event.close)
        super().closeEvent(event)


@sc.event(Event.open)
def show_trial_signup_dialog(hypertts) -> config_models.TrialRequestReponse:
    """Show dialog for HyperTTS Pro trial signup
    Returns:
        TrialRequestReponse with signup result, or None if user cancelled
    """
    dialog = TrialSignupDialog(hypertts)
    hypertts.anki_utils.wait_for_dialog_input(dialog, constants.DIALOG_ID_TRIAL_SIGNUP)
    return dialog.get_trial_result()
