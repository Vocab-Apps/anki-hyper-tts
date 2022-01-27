import sys
import PyQt5
import logging

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)


class Configuration(component_common.ConfigComponentBase):

    STACK_LEVEL_SERVICE = 0
    STACK_LEVEL_CLT = 1

    def __init__(self, hypertts, dialog):
        self.hypertts = hypertts
        self.dialog = dialog
        self.model = config_models.Configuration()
        self.service_stack_map = {}

    def get_model(self):
        return self.model

    def load_model(self, model):
        self.model = model

    def model_change(self):
        self.save_button.setEnabled(True)
        self.save_button.setStyleSheet(self.hypertts.anki_utils.get_green_stylesheet())

    def get_hypertts_pro_api_key_change_fn(self):
        def change(api_key):
            logging.info('hypertts pro api key change')
            self.model.set_hypertts_pro_api_key(api_key)
            self.model_change()
            self.set_cloud_language_tools_enabled()
        return change

    def get_service_enable_change_fn(self, service):
        def enable_change(value):
            enabled = value == 2
            logging.info(f'{service.name} enabled: {enabled}')
            self.model.set_service_enabled(service.name, enabled)
            self.model_change()
        return enable_change

    def get_service_config_str_change_fn(self, service, key):
        def str_change(text):
            logging.info(f'{service.name} {key}: {text}')
            self.model.set_service_configuration_key(service.name, key, text)
            self.model_change()
        return str_change

    def get_service_config_int_change_fn(self, service, key):
        def int_change(value):
            logging.info(f'{service.name} {key}: {value}')
            self.model.set_service_configuration_key(service.name, key, value)
            self.model_change()
        return int_change

    def get_service_config_list_change_fn(self, service, key):
        def list_change(text):
            logging.info(f'{service.name} {key}: {text}')
            self.model.set_service_configuration_key(service.name, key, text)
            self.model_change()
        return list_change

    def cloud_language_tools_enabled(self):
        return self.model.hypertts_pro_api_key_set()

    def set_cloud_language_tools_enabled(self):
        # will enable/disable checkboxes
        for service in self.hypertts.service_manager.get_all_services():
            self.manage_service_stack(service, self.service_stack_map[service.name])

    def manage_service_stack(self, service, stack):
        if self.cloud_language_tools_enabled() and service.cloudlanguagetools_enabled():
            logging.info(f'{service.name}: show CLT stack')
            stack.setCurrentIndex(self.STACK_LEVEL_CLT)
        else:
            logging.info(f'{service.name}: show service stack')
            stack.setCurrentIndex(self.STACK_LEVEL_SERVICE)

    def get_service_enabled_widget_name(self, service):
        return f'{service.name}_enabled'

    def draw_service_options(self, service, layout):
        service_enabled_checkbox = PyQt5.QtWidgets.QCheckBox('Enable')
        service_enabled_checkbox.setObjectName(self.get_service_enabled_widget_name(service))
        service_enabled_checkbox.setChecked(self.model.get_service_enabled(service.name))
        service_enabled_checkbox.stateChanged.connect(self.get_service_enable_change_fn(service))
        layout.addWidget(service_enabled_checkbox)

        configuration_options = service.configuration_options()
        options_gridlayout = PyQt5.QtWidgets.QGridLayout()
        row = 0
        for key, type in configuration_options.items():
            widget_name = f'{service.name}_{key}'
            options_gridlayout.addWidget(PyQt5.QtWidgets.QLabel(key + ':'), row, 0, 1, 1)
            if type == str:
                lineedit = PyQt5.QtWidgets.QLineEdit()
                lineedit.setText(self.model.get_service_configuration_key(service.name, key))
                lineedit.setObjectName(widget_name)
                lineedit.textChanged.connect(self.get_service_config_str_change_fn(service, key))
                options_gridlayout.addWidget(lineedit, row, 1, 1, 1)
            elif type == int:
                spinbox = PyQt5.QtWidgets.QSpinBox()
                saved_value = self.model.get_service_configuration_key(service.name, key)
                if saved_value != None:
                    spinbox.setValue(saved_value)
                spinbox.setObjectName(widget_name)
                spinbox.valueChanged.connect(self.get_service_config_int_change_fn(service, key))
                options_gridlayout.addWidget(spinbox, row, 1, 1, 1)
            elif isinstance(type, list):
                combobox = PyQt5.QtWidgets.QComboBox()
                combobox.setObjectName(widget_name)
                combobox.addItems(type)
                combobox.setCurrentText(self.model.get_service_configuration_key(service.name, key))
                combobox.currentTextChanged.connect(self.get_service_config_list_change_fn(service, key))
                options_gridlayout.addWidget(combobox, row, 1, 1, 1)
            row += 1
        
        layout.addLayout(options_gridlayout)

    def draw_service(self, service, layout):
        logging.info(f'draw_service {service.name}')
        service_groupbox = PyQt5.QtWidgets.QGroupBox(service.name)

        # add service config options, when cloudlanguagetools not enabled
        # ===============================================================

        service_stack = PyQt5.QtWidgets.QWidget()
        service_vlayout = PyQt5.QtWidgets.QVBoxLayout()
        self.draw_service_options(service, service_vlayout)
        service_stack.setLayout(service_vlayout)

        # when cloudlanguagetools is enabled
        # ==================================
        clt_stack = PyQt5.QtWidgets.QWidget()
        clt_vlayout = PyQt5.QtWidgets.QVBoxLayout()
        clt_vlayout.addWidget(PyQt5.QtWidgets.QLabel('HyperTTS Pro'))
        clt_stack.setLayout(clt_vlayout)

        # create the stack widget
        # =======================
        stack_widget = PyQt5.QtWidgets.QStackedWidget()
        stack_widget.addWidget(service_stack)
        stack_widget.addWidget(clt_stack)

        self.manage_service_stack(service, stack_widget)

        self.service_stack_map[service.name] = stack_widget

        combined_service_vlayout = PyQt5.QtWidgets.QVBoxLayout()
        combined_service_vlayout.addWidget(stack_widget)

        service_groupbox.setLayout(combined_service_vlayout)

        layout.addWidget(service_groupbox)

    def draw(self, layout):
        self.global_vlayout = PyQt5.QtWidgets.QVBoxLayout()

        # hypertts pro
        # ============

        groupbox = PyQt5.QtWidgets.QGroupBox('HyperTTS Pro')
        vlayout = PyQt5.QtWidgets.QVBoxLayout()

        vlayout.addWidget(PyQt5.QtWidgets.QLabel('API Key'))
        self.hypertts_pro_api_key = PyQt5.QtWidgets.QLineEdit()
        self.hypertts_pro_api_key.setText(self.model.hypertts_pro_api_key)
        self.hypertts_pro_api_key.textChanged.connect(self.get_hypertts_pro_api_key_change_fn())
        vlayout.addWidget(self.hypertts_pro_api_key)

        groupbox.setLayout(vlayout)
        self.global_vlayout.addWidget(groupbox)

        # services
        # ========

        groupbox = PyQt5.QtWidgets.QGroupBox('Services')
        vlayout = PyQt5.QtWidgets.QVBoxLayout()
        for service in self.hypertts.service_manager.get_all_services():
            self.draw_service(service, vlayout)

        groupbox.setLayout(vlayout)
        self.global_vlayout.addWidget(groupbox)

        # bottom buttons
        # ==============

        hlayout = PyQt5.QtWidgets.QHBoxLayout()
        self.save_button = PyQt5.QtWidgets.QPushButton('Save')
        self.save_button.setEnabled(False)
        self.cancel_button = PyQt5.QtWidgets.QPushButton('Cancel')
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        hlayout.addStretch()
        hlayout.addWidget(self.save_button)
        hlayout.addWidget(self.cancel_button)
        self.global_vlayout.addLayout(hlayout)

        # wire events
        # ===========
        self.save_button.pressed.connect(self.save_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        layout.addLayout(self.global_vlayout)

    def save_button_pressed(self):
        self.hypertts.save_configuration(self.model)
        self.dialog.close()

    def cancel_button_pressed(self):
        self.dialog.close()