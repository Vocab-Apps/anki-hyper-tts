from pydoc import describe
import sys
import aqt.qt
import webbrowser

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)


class Configuration(component_common.ConfigComponentBase):

    STACK_LEVEL_LITE = 0
    STACK_LEVEL_PRO = 1

    def __init__(self, hypertts, dialog):
        self.hypertts = hypertts
        self.dialog = dialog
        self.model = config_models.Configuration()
        self.service_stack_map = {}
        self.clt_stack_map = {}
        self.account_info = None
        self.api_key_valid = False
        self.enable_model_change = False

    def get_model(self):
        return self.model

    def load_model(self, model):
        self.model = model

    def model_change(self):
        if self.enable_model_change:
            self.save_button.setEnabled(True)
            self.save_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())

    def get_service_enable_change_fn(self, service):
        def enable_change(value):
            enabled = value == 2
            logger.info(f'{service.name} enabled: {enabled}')
            self.model.set_service_enabled(service.name, enabled)
            self.model_change()
        return enable_change

    def get_service_config_str_change_fn(self, service, key):
        def str_change(text):
            logger.info(f'{service.name} {key}: {text}')
            self.model.set_service_configuration_key(service.name, key, text)
            self.model_change()
        return str_change

    def get_service_config_int_change_fn(self, service, key):
        def int_change(value):
            logger.info(f'{service.name} {key}: {value}')
            self.model.set_service_configuration_key(service.name, key, value)
            self.model_change()
        return int_change

    def get_service_config_float_change_fn(self, service, key):
        def float_change(value):
            logger.info(f'{service.name} {key}: {value}')
            self.model.set_service_configuration_key(service.name, key, value)
            self.model_change()
        return float_change

    def get_service_config_list_change_fn(self, service, key):
        def list_change(text):
            logger.info(f'{service.name} {key}: {text}')
            self.model.set_service_configuration_key(service.name, key, text)
            self.model_change()
        return list_change

    def get_service_config_bool_change_fn(self, service, key):
        def bool_change(checkbox_value):
            value = checkbox_value == 2
            logger.info(f'{service.name} {key}: {value}')
            self.model.set_service_configuration_key(service.name, key, value)
            self.model_change()
        return bool_change

    def cloud_language_tools_enabled(self):
        return self.api_key_valid

    def set_cloud_language_tools_enabled(self):
        if self.cloud_language_tools_enabled():
            self.header_logo_stack_widget.setCurrentIndex(self.STACK_LEVEL_PRO)
        else:
            self.header_logo_stack_widget.setCurrentIndex(self.STACK_LEVEL_LITE)
        # will enable/disable checkboxes
        for service in self.hypertts.service_manager.get_all_services():
            self.manage_service_stack(service, self.service_stack_map[service.name], self.clt_stack_map[service.name])

    def manage_service_stack(self, service, service_stack, clt_stack):
        if self.cloud_language_tools_enabled() and service.cloudlanguagetools_enabled():
            logger.info(f'{service.name}: show CLT stack')
            service_stack.setVisible(False)
            clt_stack.setVisible(True)
        else:
            logger.info(f'{service.name}: show service stack')
            service_stack.setVisible(True)
            clt_stack.setVisible(False)

    def get_service_enabled_widget_name(self, service):
        return f'{service.name}_enabled'

    def draw_service_options(self, service, layout):
        service_enabled_checkbox = aqt.qt.QCheckBox('Enable')
        service_enabled_checkbox.setObjectName(self.get_service_enabled_widget_name(service))
        service_enabled_checkbox.setChecked(service.enabled)
        service_enabled_checkbox.stateChanged.connect(self.get_service_enable_change_fn(service))
        layout.addWidget(service_enabled_checkbox)

        configuration_options = service.configuration_options()
        options_gridlayout = aqt.qt.QGridLayout()
        row = 0
        for key, type in configuration_options.items():
            widget_name = f'{service.name}_{key}'
            options_gridlayout.addWidget(aqt.qt.QLabel(key + ':'), row, 0, 1, 1)
            if type == str:
                lineedit = aqt.qt.QLineEdit()
                lineedit.setText(self.model.get_service_configuration_key(service.name, key))
                lineedit.setObjectName(widget_name)
                lineedit.textChanged.connect(self.get_service_config_str_change_fn(service, key))
                options_gridlayout.addWidget(lineedit, row, 1, 1, 1)
            elif type == int:
                spinbox = aqt.qt.QSpinBox()
                saved_value = self.model.get_service_configuration_key(service.name, key)
                if saved_value != None:
                    spinbox.setValue(saved_value)
                spinbox.setObjectName(widget_name)
                spinbox.valueChanged.connect(self.get_service_config_int_change_fn(service, key))
                options_gridlayout.addWidget(spinbox, row, 1, 1, 1)
            elif type == float:
                spinbox = aqt.qt.QDoubleSpinBox()
                saved_value = self.model.get_service_configuration_key(service.name, key)
                if saved_value != None:
                    spinbox.setValue(saved_value)
                spinbox.setObjectName(widget_name)
                spinbox.valueChanged.connect(self.get_service_config_float_change_fn(service, key))
                options_gridlayout.addWidget(spinbox, row, 1, 1, 1)                
            elif type == bool:
                checkbox = aqt.qt.QCheckBox()
                saved_value = self.model.get_service_configuration_key(service.name, key)
                if saved_value != None:
                    checkbox.setChecked(saved_value)
                checkbox.setObjectName(widget_name)
                checkbox.stateChanged.connect(self.get_service_config_bool_change_fn(service, key))
                options_gridlayout.addWidget(checkbox, row, 1, 1, 1)
            elif isinstance(type, list):
                combobox = aqt.qt.QComboBox()
                combobox.setObjectName(widget_name)
                combobox.addItems(type)
                combobox.setCurrentText(self.model.get_service_configuration_key(service.name, key))
                combobox.currentTextChanged.connect(self.get_service_config_list_change_fn(service, key))
                options_gridlayout.addWidget(combobox, row, 1, 1, 1)
            row += 1
        
        layout.addLayout(options_gridlayout)

    def draw_service(self, service, layout):
        logger.info(f'draw_service {service.name}')
        
        def get_service_header_label(service):
            header_label = gui_utils.get_service_header_label(service.name)
            return header_label        

        def get_service_description_label(service):
            service_description = f'{service.service_fee.name}, {service.service_type.description}'
            service_description_label = aqt.qt.QLabel(service_description)
            service_description_label.setMargin(0)
            return service_description_label            

        combined_service_vlayout = aqt.qt.QVBoxLayout()
        # leave some space above/below services
        combined_service_vlayout.setContentsMargins(0, 5, 0, 5)

        # draw service header and description
        # ===================================

        combined_service_vlayout.addWidget(get_service_header_label(service))
        combined_service_vlayout.addWidget(get_service_description_label(service))

        # add service config options, when cloudlanguagetools not enabled
        # ===============================================================

        service_stack = aqt.qt.QWidget()
        service_vlayout = aqt.qt.QVBoxLayout()
        service_vlayout.setContentsMargins(0, 0, 0, 0)
        if service.cloudlanguagetools_enabled():
            hlayout = aqt.qt.QHBoxLayout()
            logo = gui_utils.get_graphic(constants.GRAPHICS_SERVICE_COMPATIBLE)
            hlayout.addStretch()
            hlayout.addWidget(logo)
            service_vlayout.addLayout(hlayout)
        self.draw_service_options(service, service_vlayout)
        service_stack.setLayout(service_vlayout)

        # when cloudlanguagetools is enabled
        # ==================================
        clt_stack = aqt.qt.QWidget()
        clt_vlayout = aqt.qt.QVBoxLayout()
        clt_vlayout.setContentsMargins(0, 0, 0, 0)
        logo = gui_utils.get_graphic(constants.GRAPHICS_SERVICE_ENABLED)
        clt_vlayout.addWidget(logo)
        clt_stack.setLayout(clt_vlayout)


        self.manage_service_stack(service, service_stack, clt_stack)

        self.service_stack_map[service.name] = service_stack
        self.clt_stack_map[service.name] = clt_stack

        combined_service_vlayout.addWidget(service_stack)
        combined_service_vlayout.addWidget(clt_stack)

        layout.addLayout(combined_service_vlayout)

    def draw(self, layout):
        self.global_vlayout = aqt.qt.QVBoxLayout()

        # logo header
        # ===========
        lite_stack = aqt.qt.QWidget()
        pro_stack = aqt.qt.QWidget()

        lite_stack.setLayout(gui_utils.get_hypertts_label_header(False))
        pro_stack.setLayout(gui_utils.get_hypertts_label_header(True))

        self.header_logo_stack_widget = aqt.qt.QStackedWidget()
        self.header_logo_stack_widget.addWidget(lite_stack)
        self.header_logo_stack_widget.addWidget(pro_stack)

        self.header_logo_stack_widget.setCurrentIndex(self.STACK_LEVEL_LITE) # lite
        self.global_vlayout.addWidget(self.header_logo_stack_widget)

        # hypertts pro
        # ============

        groupbox = aqt.qt.QGroupBox('HyperTTS Pro')
        vlayout = aqt.qt.QVBoxLayout()

        description_label = aqt.qt.QLabel(constants.GUI_TEXT_HYPERTTS_PRO)
        description_label.setWordWrap(True)
        vlayout.addWidget(description_label)
        vlayout.addWidget(aqt.qt.QLabel('API Key'))
        self.hypertts_pro_api_key = aqt.qt.QLineEdit()
        self.hypertts_pro_api_key.setText(self.model.hypertts_pro_api_key)
        # self.hypertts_pro_api_key.textChanged.connect(self.get_hypertts_pro_api_key_change_fn())
        vlayout.addWidget(self.hypertts_pro_api_key)

        self.account_info_label = aqt.qt.QLabel()
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

        groupbox.setLayout(vlayout)
        self.global_vlayout.addWidget(groupbox)


        # services
        # ========

        def get_separator():
            separator = aqt.qt.QFrame()
            separator.setFrameShape(aqt.qt.QFrame.HLine)
            separator.setSizePolicy(aqt.qt.QSizePolicy.Minimum, aqt.qt.QSizePolicy.Expanding)
            separator.setStyleSheet('color: #cccccc;')
            separator.setLineWidth(2)
            return separator

        self.global_vlayout.addWidget(aqt.qt.QLabel('Services'))
        services_scroll_area = aqt.qt.QScrollArea()
        services_scroll_area.setHorizontalScrollBarPolicy(aqt.qt.Qt.ScrollBarAlwaysOff)
        services_scroll_area.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignHCenter)
        services_widget = aqt.qt.QWidget()
        services_vlayout = aqt.qt.QVBoxLayout(services_widget)
        
        def service_sort_key(service):
            return service.name
        service_list = self.hypertts.service_manager.get_all_services()
        service_list.sort(key=service_sort_key)
        for service in service_list:
            self.draw_service(service, services_vlayout)
            services_vlayout.addWidget(get_separator())

        services_scroll_area.setWidget(services_widget)
        self.global_vlayout.addWidget(services_scroll_area, 1)

        # bottom buttons
        # ==============

        hlayout = aqt.qt.QHBoxLayout()
        self.save_button = aqt.qt.QPushButton('Save')
        self.save_button.setEnabled(False)
        self.cancel_button = aqt.qt.QPushButton('Cancel')
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        hlayout.addStretch()
        hlayout.addWidget(self.save_button)
        hlayout.addWidget(self.cancel_button)
        self.global_vlayout.addLayout(hlayout)

        # wire events
        # ===========
        self.save_button.pressed.connect(self.save_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        self.hypertts.anki_utils.wire_typing_timer(self.hypertts_pro_api_key, self.pro_api_key_entered)

        # run event once
        self.pro_api_key_entered()
        self.enable_model_change = True

        layout.addLayout(self.global_vlayout)


    def pro_api_key_entered(self):
        # get data for the API key in the background
        api_key = self.hypertts_pro_api_key.text()
        if len(api_key) > 0:
            self.api_key = api_key.strip()
            logger.info(f'verifying api_key [{self.api_key}]')
            self.account_info_label.setText('Verifying...')
            self.hypertts.anki_utils.run_in_background(self.get_account_data_task, self.get_account_data_task_done)
        else:
            self.udpdate_gui_state_api_key_not_valid()


    def get_account_data_task(self):
        return self.hypertts.service_manager.cloudlanguagetools.account_info(self.api_key)

    def get_account_data_task_done(self, result):
        with self.hypertts.error_manager.get_single_action_context('Getting Account Data'):
            self.account_info = result.result()
            self.hypertts.anki_utils.run_on_main(self.update_pro_status)

    def udpdate_gui_state_api_key_not_valid(self):
        self.api_key_valid = False
        self.model.set_hypertts_pro_api_key(None)
        self.account_info_label.setText('')
        self.account_update_button.setVisible(False)
        self.account_cancel_button.setVisible(False)
        self.model_change()
        self.set_cloud_language_tools_enabled()

    def udpdate_gui_state_api_key_valid(self, api_key):
        self.api_key_valid = True
        self.model.set_hypertts_pro_api_key(self.api_key)
        self.model_change()
        self.set_cloud_language_tools_enabled()        

    def update_pro_status(self):
        logger.info('update_pro_status')
        if 'error' in self.account_info:
            self.udpdate_gui_state_api_key_not_valid()
        else:
            self.udpdate_gui_state_api_key_valid(self.api_key)
        # update account info label
        lines = []
        for key, value in self.account_info.items():
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


    def save_button_pressed(self):
        with self.hypertts.error_manager.get_single_action_context('Saving Service Configuration'):
            self.hypertts.save_configuration(self.model)
            self.hypertts.service_manager.configure(self.model)
            self.dialog.close()

    def cancel_button_pressed(self):
        self.dialog.close()