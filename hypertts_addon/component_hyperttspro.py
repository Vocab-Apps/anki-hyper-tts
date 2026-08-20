import sys
import aqt.qt
import webbrowser
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

class HyperTTSPro(component_common.ConfigComponentBase):
    PRO_STACK_LEVEL_BUTTONS = 0 # show all the buttons
    PRO_STACK_LEVEL_TRIAL   = 1 # ask user to enter email
    PRO_STACK_LEVEL_API_KEY = 2 # ask user to enter API key
    PRO_STACK_LEVEL_ENABLED = 3 # hypertts pro already setup

    def __init__(self, hypertts, model_change_callback, save_blocked_change_callback=None):
        self.hypertts = hypertts
        self.model_change_callback = model_change_callback
        # optional, lets the screen we're embedded in disable its Save button while an API key is
        # being verified (github issue #360)
        self.save_blocked_change_callback = save_blocked_change_callback
        self.model = config_models.HyperTTSProAccountConfig()
        # number of API key verifications currently in flight
        self.api_key_verification_count = 0
        # the last API key we got a verification answer for, valid or not
        self.last_verified_api_key = None

    def get_model(self):
        return self.model

    def load_model(self, model: config_models.HyperTTSProAccountConfig):
        self.model = model

    def report_model_change(self):
        self.model_change_callback(self.get_model())

    # API key verification state
    # ==========================

    def api_key_input_pending_verification(self) -> bool:
        """whether the API key field holds something which hasn't been through verification yet.
        the typing timer only fires a second after the user stops typing, and the request itself
        takes longer still: that whole window has to count as pending, otherwise a save landing in
        it writes the API key the screen held before the user started typing."""
        if self.hypertts_pro_stack.currentIndex() != self.PRO_STACK_LEVEL_API_KEY:
            return False
        entered_api_key = self.hypertts_pro_api_key.text().strip()
        if len(entered_api_key) == 0:
            return False
        return entered_api_key != self.last_verified_api_key

    def save_blocked_reason(self):
        """why the configuration must not be saved right now, or None if it can be"""
        if self.api_key_verification_count > 0 or self.api_key_input_pending_verification():
            return constants.GUI_TEXT_HYPERTTS_PRO_VERIFYING_API_KEY
        return None

    def report_save_blocked_change(self, *args):
        # *args: also wired directly to qt signals which pass the changed value
        if self.save_blocked_change_callback != None:
            self.save_blocked_change_callback(self.save_blocked_reason())

    def draw_hypertts_pro_stack_buttons(self):
        buttons_stack = aqt.qt.QWidget()
        vlayout = aqt.qt.QVBoxLayout()

        description_label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO)
        description_label.setWordWrap(True)
        vlayout.addWidget(description_label)

        buttons_layout = aqt.qt.QGridLayout()
        def draw_button_component(buttons_layout, column, text_button, text_label):
            button = aqt.qt.QPushButton(text_button)
            label = gui_utils.get_small_cta_label(text_label)
            label.setWordWrap(True)
            buttons_layout.addWidget(button, 0, column, 1, 1)
            buttons_layout.addWidget(label, 1, column, 1, 1)

            return button
        # trial
        self.trial_button = draw_button_component(buttons_layout, 0, constants.GUI_TEXT_BUTTON_TRIAL, constants.GUI_TEXT_HYPERTTS_PRO_TRIAL)
        self.trial_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        font_large = aqt.qt.QFont()
        font_large.setBold(True)
        self.trial_button.setFont(font_large)        
        # buy plan 
        self.buy_plan_button = draw_button_component(buttons_layout, 1, constants.GUI_TEXT_BUTTON_BUY, constants.GUI_TEXT_HYPERTTS_PRO_BUY_PLAN)
        # enter API key
        self.enter_api_key_button = draw_button_component(buttons_layout, 2, constants.GUI_TEXT_BUTTON_API_KEY, constants.GUI_TEXT_HYPERTTS_PRO_ENTER_API_KEY)
        buttons_layout.setColumnStretch(0, 10)
        buttons_layout.setColumnStretch(1, 10)
        buttons_layout.setColumnStretch(2, 10)

        vlayout.addLayout(buttons_layout)
        buttons_stack.setLayout(vlayout)

        return buttons_stack

    def draw_hypertts_pro_stack_trial(self):
        trial_stack = aqt.qt.QWidget()
        vlayout = aqt.qt.QVBoxLayout()
        label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO_TRIAL_ENTER_EMAIL)
        label.setWordWrap(True)
        vlayout.addWidget(label)
        self.trial_email_input = aqt.qt.QLineEdit()
        self.trial_email_input.setPlaceholderText("Enter your email (no disposable email addresses)")
        vlayout.addWidget(self.trial_email_input)
        
        password_label = aqt.qt.QLabel("Password:")
        vlayout.addWidget(password_label)
        self.trial_password_input = aqt.qt.QLineEdit()
        self.trial_password_input.setPlaceholderText("Choose a password")
        self.trial_password_input.setEchoMode(aqt.qt.QLineEdit.EchoMode.Password)
        vlayout.addWidget(self.trial_password_input)
        
        self.trial_email_validation_label = aqt.qt.QLabel()
        self.trial_email_validation_label.setWordWrap(True)
        vlayout.addWidget(self.trial_email_validation_label)
        
        hlayout = aqt.qt.QHBoxLayout()
        self.enter_trial_email_ok_button = aqt.qt.QPushButton('OK')
        hlayout.addWidget(self.enter_trial_email_ok_button)
        self.enter_trial_email_cancel_button = aqt.qt.QPushButton('Cancel')
        hlayout.addWidget(self.enter_trial_email_cancel_button)
        vlayout.addLayout(hlayout)

        vlayout.addStretch()
        trial_stack.setLayout(vlayout)

        return trial_stack

    def draw_hypertts_pro_stack_api_key(self):
        api_key_stack = aqt.qt.QWidget()
        vlayout = aqt.qt.QVBoxLayout()
        vlayout.addWidget(aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO_ENTER_API_KEY))
        self.hypertts_pro_api_key = aqt.qt.QLineEdit()
        self.hypertts_pro_api_key.setObjectName('hypertts_hyperttspro_api_key_input')
        vlayout.addWidget(self.hypertts_pro_api_key)

        self.api_key_validation_label = aqt.qt.QLabel()
        self.api_key_validation_label.setObjectName('hypertts_hyperttspro_api_key_validation_label')
        # the server's error message can be a full sentence, don't let it run off the dialog
        self.api_key_validation_label.setWordWrap(True)
        vlayout.addWidget(self.api_key_validation_label)

        # this screen doubles as the "your API key could not be verified" screen: when there is
        # still an API key in the configuration, say that we kept it and let the user remove it
        # themselves, rather than removing it for them (github issue #360)
        self.api_key_kept_label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO_API_KEY_KEPT)
        self.api_key_kept_label.setObjectName('hypertts_hyperttspro_api_key_kept_label')
        self.api_key_kept_label.setWordWrap(True)
        self.api_key_kept_label.setVisible(False)
        vlayout.addWidget(self.api_key_kept_label)

        self.remove_kept_api_key_button = aqt.qt.QPushButton('Remove API Key')
        self.remove_kept_api_key_button.setObjectName('hypertts_hyperttspro_remove_kept_api_key_button')
        self.remove_kept_api_key_button.setVisible(False)
        vlayout.addWidget(self.remove_kept_api_key_button)

        self.enter_api_key_cancel_button = aqt.qt.QPushButton('Cancel')
        self.enter_api_key_cancel_button.setObjectName('hypertts_hyperttspro_enter_api_key_cancel_button')
        vlayout.addWidget(self.enter_api_key_cancel_button)

        vlayout.addStretch()

        api_key_stack.setLayout(vlayout)

        return api_key_stack        

    def draw_hypertts_pro_stack_enabled(self):
        enabled_stack = aqt.qt.QWidget()
        vlayout = aqt.qt.QVBoxLayout()

        enabled_label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO_ENABLED)
        vlayout.addWidget(enabled_label)

        self.api_key_label = aqt.qt.QLabel()
        self.api_key_label.setTextInteractionFlags(aqt.qt.Qt.TextInteractionFlag.TextSelectableByMouse)
        vlayout.addWidget(self.api_key_label)

        self.account_info_label = aqt.qt.QLabel()
        self.account_info_label.setTextInteractionFlags(aqt.qt.Qt.TextInteractionFlag.TextSelectableByMouse)
        vlayout.addWidget(self.account_info_label)

        self.account_update_button = aqt.qt.QPushButton()
        self.account_update_button.setText('Upgrade / Downgrade / Payment options')
        self.account_update_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())
        self.account_cancel_button = aqt.qt.QPushButton()
        self.account_cancel_button.setText('Cancel Plan')
        self.account_cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        vlayout.addWidget(self.account_update_button)
        vlayout.addWidget(self.account_cancel_button)
        self.account_update_button.setVisible(False)
        self.account_cancel_button.setVisible(False)

        self.remove_api_key_button = aqt.qt.QPushButton('Remove API Key')
        self.remove_api_key_button.setObjectName('hypertts_hyperttspro_remove_api_key_button')
        vlayout.addWidget(self.remove_api_key_button)

        vlayout.addStretch()

        enabled_stack.setLayout(vlayout)

        return enabled_stack


    def draw_widget(self):
        """draw into a widget of our own, for callers which put this component in a tab"""
        widget = aqt.qt.QWidget()
        vlayout = aqt.qt.QVBoxLayout(widget)
        self.draw(vlayout)
        vlayout.addStretch()
        return widget

    def draw(self, global_vlayout):
        groupbox = aqt.qt.QGroupBox('HyperTTS Pro')

        self.hypertts_pro_stack = aqt.qt.QStackedWidget()        

        # draw buttons
        # ============
        buttons_stack = self.draw_hypertts_pro_stack_buttons()

        # draw trial / email input
        # ========================
        trial_stack = self.draw_hypertts_pro_stack_trial()

        # draw enter API key
        # ==================
        api_key_stack = self.draw_hypertts_pro_stack_api_key()

        # draw hypertts pro enabled
        # =========================
        enabled_stack = self.draw_hypertts_pro_stack_enabled()

        self.hypertts_pro_stack.addWidget(buttons_stack)
        self.hypertts_pro_stack.addWidget(trial_stack)
        self.hypertts_pro_stack.addWidget(api_key_stack)
        self.hypertts_pro_stack.addWidget(enabled_stack)

        vlayout = aqt.qt.QVBoxLayout()
        vlayout.addWidget(self.hypertts_pro_stack)
        groupbox.setLayout(vlayout)

        # wire events
        # ===========
        self.trial_button.pressed.connect(self.trial_button_pressed)
        self.enter_api_key_button.pressed.connect(self.enter_api_key_button_pressed)
        self.enter_trial_email_cancel_button.pressed.connect(self.action_cancel_button_pressed)
        self.enter_api_key_cancel_button.pressed.connect(self.action_cancel_button_pressed)
        self.buy_plan_button.pressed.connect(self.signup_button_pressed)
        self.remove_api_key_button.pressed.connect(self.remove_api_key_button_pressed)
        self.remove_kept_api_key_button.pressed.connect(self.remove_api_key_button_pressed)
        self.enter_trial_email_ok_button.pressed.connect(self.trial_button_ok_pressed)

        # whether saving has to wait depends on which screen we're on and on what the user typed
        # into the API key field, so recompute it on both
        self.hypertts_pro_stack.currentChanged.connect(self.report_save_blocked_change)
        self.hypertts_pro_api_key.textChanged.connect(self.report_save_blocked_change)

        self.hypertts_pro_api_key_timer = self.hypertts.anki_utils.wire_typing_timer(self.hypertts_pro_api_key, self.pro_api_key_entered)

        if self.model.api_key != None:
            self.hypertts_pro_api_key.setText(self.model.api_key)
            self.verify_api_key(self.model.api_key)

        global_vlayout.addWidget(groupbox)

    @sc.event(Event.click_free_trial)
    def trial_button_pressed(self):
        self.trial_email_validation_label.setText('')
        self.hypertts_pro_stack.setCurrentIndex(self.PRO_STACK_LEVEL_TRIAL)

    @sc.event(Event.click_enter_api_key)
    def enter_api_key_button_pressed(self):
        self.api_key_validation_label.setText('')
        self.hypertts_pro_stack.setCurrentIndex(self.PRO_STACK_LEVEL_API_KEY)

    @sc.event(Event.click_sign_up)
    def signup_button_pressed(self):
        logger.info('opening signup page')
        webbrowser.open(constants.BUY_PLAN_URL)

    @sc.event(Event.click_cancel)
    def action_cancel_button_pressed(self):
        self.hypertts_pro_stack.setCurrentIndex(self.PRO_STACK_LEVEL_BUTTONS)

    @sc.event(Event.click_remove_api_key)
    def remove_api_key_button_pressed(self):
        # logged explicitly (and not only through the stats event) so that the sentry breadcrumbs
        # always tell us the API key was removed by the user, rather than cleared by HyperTTS
        # itself after a failed verification (github issue #360)
        logger.info('user pressed the remove API key button, clearing the API key')
        self.model.clear_api_key()
        self.hypertts_pro_stack.setCurrentIndex(self.PRO_STACK_LEVEL_BUTTONS)
        self.hypertts_pro_api_key.setText('')
        self.api_key_validation_label.setText('')
        self.update_api_key_stack_state()
        self.report_model_change()

    @sc.event(Event.click_free_trial_ok)
    def trial_button_ok_pressed(self):
        self.trial_email_validation_label.setText('Verifying...')
        self.email = self.trial_email_input.text()
        self.password = self.trial_password_input.text()
        self.hypertts.anki_utils.run_in_background(self.trial_email_signup_task, self.trial_email_signup_task_done)

    def trial_email_signup_task(self):
        client_uuid = self.hypertts.get_client_uuid()
        return self.hypertts.service_manager.cloudlanguagetools.request_trial_key(self.email, self.password, client_uuid)

    def trial_email_signup_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Signing up for trial'):
            trial_signup_result = result.result()
            logger.debug(f'trial_signup_result: {trial_signup_result}')
            self.hypertts.anki_utils.run_on_main(lambda: self.trial_email_signup_update(trial_signup_result))

    def trial_email_signup_update(self, trial_signup_result: config_models.TrialRequestReponse):
        logger.info(f'trial_signup_result: {pprint.pformat(trial_signup_result)}')
        if trial_signup_result.success == False:
            self.trial_email_validation_label.setText(trial_signup_result.error)
        else:
            # the key is only written to the model once it has verified, see verify_api_key
            self.verify_api_key(trial_signup_result.api_key)
            # Add warning about email confirmation
            self.hypertts.anki_utils.info_message(constants.GUI_TEXT_HYPERTTS_PRO_TRIAL_CONFIRM_EMAIL, None)

    def pro_api_key_entered(self):
        if self.hypertts_pro_stack.currentIndex() == self.PRO_STACK_LEVEL_API_KEY:
            # only react if we're currently expecting the user to enter their API key
            # get data for the API key in the background
            api_key = self.hypertts_pro_api_key.text()
            if len(api_key) > 0:
                self.verify_api_key(api_key.strip())
            else:
                self.api_key_validation_label.setText(f'<b>error</b>: please enter API key')

    def verify_api_key(self, api_key):
        """verify api_key with the server. the key is deliberately not written to the model here:
        the model only ever receives an API key which verified, or a removal the user asked for.
        that way a verification which fails, or which the user saves over before it comes back,
        can never replace the API key sitting in the configuration (github issue #360)."""
        logger.info(f'verifying api_key [{api_key}]')
        self.api_key_validation_label.setText('Verifying...')
        # self.account_info_label.setText('Verifying...')
        self.api_key_verification_count += 1
        self.report_save_blocked_change()

        def get_account_data_task():
            return self.hypertts.service_manager.cloudlanguagetools.account_info(api_key)

        def get_account_data_task_done(result):
            try:
                with self.hypertts.error_manager.get_single_action_context('Getting Account Data'):
                    account_info_result = result.result()
                    self.hypertts.anki_utils.run_on_main(
                        lambda: self.update_pro_status(account_info_result))
            finally:
                # always, so that a failed request doesn't leave the Save button disabled forever
                self.hypertts.anki_utils.run_on_main(
                    lambda: self.api_key_verification_done(api_key))

        self.hypertts.anki_utils.run_in_background(get_account_data_task, get_account_data_task_done)

    def api_key_verification_done(self, api_key):
        self.api_key_verification_count -= 1
        self.last_verified_api_key = api_key
        self.report_save_blocked_change()

    def update_api_key_stack_state(self):
        """show the "we kept your API key" message and its Remove button whenever the API key
        screen is displayed while an API key is still present in the configuration"""
        api_key_set = self.model.api_key != None and len(self.model.api_key) > 0
        self.api_key_kept_label.setVisible(api_key_set)
        self.remove_kept_api_key_button.setVisible(api_key_set)

    def update_pro_status(self, account_info_result):
        logger.info(f'update_pro_status {account_info_result}')

        # update account info label
        self.account_update_button.setVisible(False)
        self.account_cancel_button.setVisible(False)

        if account_info_result.api_key_valid == False:
            # API key invalid
            self.api_key_validation_label.setText(f'<b>error</b>: {account_info_result.api_key_error}')
            self.account_info_label.setText('')
            self.account_update_button.setVisible(False)
            self.account_cancel_button.setVisible(False)
            self.hypertts_pro_stack.setCurrentIndex(self.PRO_STACK_LEVEL_API_KEY)
            # the API key which is already in the configuration is deliberately left alone.
            # verification fails just as much when the servers are unreachable or erroring as when
            # the key is genuinely wrong, and quietly dropping the key on the next save is how
            # users lost their API key in github issue #360. only the Remove API Key button removes
            # a key, and only a key which verified replaces one.
            logger.info('api key verification failed, keeping the configured API key: '
                f'{account_info_result.api_key_error}')
            self.model.api_key_valid = False
            self.model.api_key_error = account_info_result.api_key_error
            self.model.account_info = None
        else:
            # API key valid
            lines = []
            for key, value in account_info_result.account_info.items():
                if key == 'update_url':
                    self.account_update_button.setVisible(True)
                    self.account_update_url = value
                    self.account_update_button.pressed.connect(lambda: webbrowser.open(self.account_update_url))
                elif key == 'cancel_url':
                    self.account_cancel_button.setVisible(True)
                    self.account_cancel_url = value
                    self.account_cancel_button.pressed.connect(lambda: webbrowser.open(self.account_cancel_url))
                else:
                    lines.append(f'<b>{key}</b>: {value}')
            self.account_info_label.setText('<br/>'.join(lines))

            self.api_key_validation_label.setText('')
            self.api_key_label.setText(f'<b>API Key:</b> {account_info_result.api_key}')
            self.hypertts_pro_stack.setCurrentIndex(self.PRO_STACK_LEVEL_ENABLED)
            self.model = account_info_result

        self.update_api_key_stack_state()
        self.report_model_change()
