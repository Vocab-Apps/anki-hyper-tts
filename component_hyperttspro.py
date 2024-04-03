import sys
import aqt.qt
import webbrowser

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)

class HyperTTSPro(component_common.ConfigComponentBase):
    PRO_STACK_LEVEL_BUTTONS = 0 # show all the buttons
    PRO_STACK_LEVEL_TRIAL   = 1 # ask user to enter email
    PRO_STACK_LEVEL_API_KEY = 2 # ask user to enter API key
    PRO_STACK_LEVEL_ENABLED = 3 # hypertts pro already setup

    def __init__(self, hypertts, model_change_callback):
        self.hypertts = hypertts
        self.model_change_callback = model_change_callback
        self.model = config_models.HyperTTSProAccountConfig()

    def get_model(self):
        return self.model

    def load_model(self, model: config_models.HyperTTSProAccountConfig):
        self.model = model

    def report_model_change(self):
        self.model_change_callback(self.get_model())

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
        vlayout.addWidget(self.trial_email_input)
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
        vlayout.addWidget(self.hypertts_pro_api_key)

        self.api_key_validation_label = aqt.qt.QLabel()
        vlayout.addWidget(self.api_key_validation_label)

        self.enter_api_key_cancel_button = aqt.qt.QPushButton('Cancel')
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
        vlayout.addWidget(self.remove_api_key_button)

        vlayout.addStretch()

        enabled_stack.setLayout(vlayout)

        return enabled_stack


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
        self.enter_trial_email_ok_button.pressed.connect(self.trial_button_ok_pressed)

        self.hypertts.anki_utils.wire_typing_timer(self.hypertts_pro_api_key, self.pro_api_key_entered)

        if self.model.api_key != None:
            self.hypertts_pro_api_key.setText(self.model.api_key)
            self.verify_api_key()

        global_vlayout.addWidget(groupbox)

    def trial_button_pressed(self):
        self.trial_email_validation_label.setText('')
        self.hypertts_pro_stack.setCurrentIndex(self.PRO_STACK_LEVEL_TRIAL)

    def enter_api_key_button_pressed(self):
        self.api_key_validation_label.setText('')
        self.hypertts_pro_stack.setCurrentIndex(self.PRO_STACK_LEVEL_API_KEY)

    def signup_button_pressed(self):
        logger.info('opening signup page')
        webbrowser.open(constants.BUY_PLAN_URL)

    def action_cancel_button_pressed(self):
        self.hypertts_pro_stack.setCurrentIndex(self.PRO_STACK_LEVEL_BUTTONS)

    def remove_api_key_button_pressed(self):
        self.model.clear_api_key()
        self.hypertts_pro_stack.setCurrentIndex(self.PRO_STACK_LEVEL_BUTTONS)
        self.hypertts_pro_api_key.setText('')
        self.report_model_change()

    def trial_button_ok_pressed(self):
        self.trial_email_validation_label.setText('Verifying...')
        self.email = self.trial_email_input.text()
        self.hypertts.anki_utils.run_in_background(self.trial_email_signup_task, self.trial_email_signup_task_done)

    def trial_email_signup_task(self):
        return self.hypertts.service_manager.cloudlanguagetools.request_trial_key(self.email)

    def trial_email_signup_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Signing up for trial'):
            trial_signup_result = result.result()
            logger.debug(f'trial_signup_result: {trial_signup_result}')
            self.hypertts.anki_utils.run_on_main(lambda: self.trial_email_signup_update(trial_signup_result))

    def trial_email_signup_update(self, trial_signup_result):
        logger.info(f'trial_signup_result: {trial_signup_result}')
        if 'error' in trial_signup_result:
            self.trial_email_validation_label.setText(trial_signup_result['error'])
        elif 'api_key' in trial_signup_result:
            self.model.api_key= trial_signup_result['api_key']
            self.verify_api_key()
        else:
            raise Exception('could not find api_key')

    def pro_api_key_entered(self):
        if self.hypertts_pro_stack.currentIndex() == self.PRO_STACK_LEVEL_API_KEY:
            # only react if we're currently expecting the user to enter their API key
            # get data for the API key in the background
            api_key = self.hypertts_pro_api_key.text()
            if len(api_key) > 0:
                self.model.api_key= api_key.strip()
                self.verify_api_key()
            else:
                self.api_key_validation_label.setText(f'<b>error</b>: please enter API key')

    def verify_api_key(self):
        logger.info(f'verifying api_key [{self.model.api_key}]')
        self.api_key_validation_label.setText('Verifying...')
        # self.account_info_label.setText('Verifying...')
        self.hypertts.anki_utils.run_in_background(self.get_account_data_task, self.get_account_data_task_done)

    def get_account_data_task(self):
        return self.hypertts.service_manager.cloudlanguagetools.account_info(self.model.api_key)

    def get_account_data_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Getting Account Data'):
            account_info_result = result.result()
            def update_pro_status_lambda():
                self.update_pro_status(account_info_result)
            self.hypertts.anki_utils.run_on_main(update_pro_status_lambda)

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
            # clear API key, it's not valid
            account_info_result.api_key = None     
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
        self.report_model_change()
