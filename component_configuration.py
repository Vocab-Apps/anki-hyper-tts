import sys
import PyQt5
import logging

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)


class Configuration(component_common.ConfigComponentBase):

    def __init__(self, hypertts, dialog):
        self.hypertts = hypertts
        self.dialog = dialog
        self.model = config_models.Configuration()

    def get_model(self):
        return self.model

    def load_model(self, model):
        self.model = model

    def get_hypertts_pro_api_key_change_fn(self):
        def change(api_key):
            logging.info('hypertts pro api key change')
            self.model.set_hypertts_pro_api_key(api_key)
        return change

    def get_service_enable_change_fn(self, service):
        def enable_change(value):
            enabled = value == 2
            logging.info(f'{service.name} enabled: {enabled}')
            self.model.set_service_enabled(service.name, enabled)
        return enable_change

    def get_service_config_str_change_fn(self, service, key):
        def str_change(text):
            logging.info(f'{service.name} {key}: {text}')
            self.model.set_service_configuration_key(service.name, key, text)
        return str_change

    def get_service_config_int_change_fn(self, service, key):
        def int_change(value):
            logging.info(f'{service.name} {key}: {value}')
            self.model.set_service_configuration_key(service.name, key, value)
        return int_change

    def get_service_config_list_change_fn(self, service, key):
        def list_change(text):
            logging.info(f'{service.name} {key}: {text}')
            self.model.set_service_configuration_key(service.name, key, text)
        return list_change


    def draw(self):
        global_vlayout = PyQt5.QtWidgets.QVBoxLayout()

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
        global_vlayout.addWidget(groupbox)

        # services
        # ========

        groupbox = PyQt5.QtWidgets.QGroupBox('Services')
        vlayout = PyQt5.QtWidgets.QVBoxLayout()
        for service in self.hypertts.service_manager.get_all_services():
            service_groupbox = PyQt5.QtWidgets.QGroupBox(service.name)
            service_vlayout = PyQt5.QtWidgets.QVBoxLayout()

            widget_name = f'{service.name}_enabled'
            service_enabled_checkbox = PyQt5.QtWidgets.QCheckBox('Enable')
            service_enabled_checkbox.setObjectName(widget_name)
            service_enabled_checkbox.setChecked(self.model.get_service_enabled(service.name))
            service_enabled_checkbox.stateChanged.connect(self.get_service_enable_change_fn(service))
            service_vlayout.addWidget(service_enabled_checkbox)

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

            service_vlayout.addLayout(options_gridlayout)
            service_groupbox.setLayout(service_vlayout)
            vlayout.addWidget(service_groupbox)
        groupbox.setLayout(vlayout)
        global_vlayout.addWidget(groupbox)

        # bottom buttons
        # ==============

        hlayout = PyQt5.QtWidgets.QHBoxLayout()
        self.save_button = PyQt5.QtWidgets.QPushButton('Save')
        self.cancel_button = PyQt5.QtWidgets.QPushButton('Cancel')
        hlayout.addStretch()
        hlayout.addWidget(self.save_button)
        hlayout.addWidget(self.cancel_button)
        global_vlayout.addLayout(hlayout)

        # wire events
        # ===========
        self.save_button.pressed.connect(self.save_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        return global_vlayout

    def save_button_pressed(self):
        self.hypertts.save_configuration(self.model)
        self.dialog.close()

    def cancel_button_pressed(self):
        self.dialog.close()