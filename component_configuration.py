import sys
import PyQt5
import logging

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)


class Configuration(component_common.ConfigComponentBase):

    def __init__(self, hypertts):
        self.hypertts = hypertts
        self.model = config_models.Configuration()

    def get_model(self):
        return self.model

    def load_model(self, model):
        self.model = model

    def get_service_config_str_change_fn(self, service, key):
        def str_change(text):
            logging.info(f'{service.name} {key}: {text}')
        return str_change

    def get_service_config_int_change_fn(self, service, key):
        def int_change(value):
            logging.info(f'{service.name} {key}: {value}')
        return int_change

    def get_service_config_list_change_fn(self, service, key):
        def list_change(text):
            logging.info(f'{service.name} {key}: {text}')
        return list_change


    def draw(self):
        global_vlayout = PyQt5.QtWidgets.QVBoxLayout()

        # hypertts pro
        # ============

        groupbox = PyQt5.QtWidgets.QGroupBox('HyperTTS Pro')
        vlayout = PyQt5.QtWidgets.QVBoxLayout()

        vlayout.addWidget(PyQt5.QtWidgets.QLabel('API Key'))
        self.hypertts_pro_api_key = PyQt5.QtWidgets.QLineEdit()
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

            service_enabled_checkbox = PyQt5.QtWidgets.QCheckBox('Enable')
            service_vlayout.addWidget(service_enabled_checkbox)

            configuration_options = service.configuration_options()
            options_gridlayout = PyQt5.QtWidgets.QGridLayout()
            row = 0
            for key, type in configuration_options.items():
                options_gridlayout.addWidget(PyQt5.QtWidgets.QLabel(key + ':'), row, 0, 1, 1)
                if type == str:
                    lineedit = PyQt5.QtWidgets.QLineEdit()
                    lineedit.textChanged.connect(self.get_service_config_str_change_fn(service, key))
                    options_gridlayout.addWidget(lineedit, row, 1, 1, 1)
                elif type == int:
                    spinbox = PyQt5.QtWidgets.QSpinBox()
                    spinbox.valueChanged.connect(self.get_service_config_int_change_fn(service, key))
                    options_gridlayout.addWidget(spinbox, row, 1, 1, 1)
                elif isinstance(type, list):
                    combobox = PyQt5.QtWidgets.QComboBox()
                    combobox.addItems(type)
                    combobox.currentTextChanged.connect(self.get_service_config_list_change_fn(service, key))
                    options_gridlayout.addWidget(combobox, row, 1, 1, 1)
                row += 1

            service_vlayout.addLayout(options_gridlayout)
            service_groupbox.setLayout(service_vlayout)
            vlayout.addWidget(service_groupbox)
        groupbox.setLayout(vlayout)
        global_vlayout.addWidget(groupbox)

        return global_vlayout
