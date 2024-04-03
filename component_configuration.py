from pydoc import describe
import sys
import aqt.qt
import webbrowser

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
component_hyperttspro = __import__('component_hyperttspro', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)

class ScrollAreaCustom(aqt.qt.QScrollArea):
    def __init__(self):
        aqt.qt.QScrollArea.__init__(self)

    def sizeHint(self):
        return aqt.qt.QSize(100, 100)

class Configuration(component_common.ConfigComponentBase):

    STACK_LEVEL_LITE = 0
    STACK_LEVEL_PRO = 1

    def __init__(self, hypertts, dialog):
        self.hypertts = hypertts
        self.dialog = dialog
        self.model = config_models.Configuration()
        self.service_stack_map = {}
        self.clt_stack_map = {}
        self.enable_model_change = False
        self.api_key_valid = False
        self.hyperttspro = component_hyperttspro.HyperTTSPro(self.hypertts, self.hyperttspro_account_config_change)

    def get_model(self):
        return self.model

    def load_model(self, model):
        self.model = model
        self.hyperttspro.load_model(self.model.get_hypertts_pro_config())

    def hyperttspro_account_config_change(self, account_config: config_models.HyperTTSProAccountConfig):
        self.api_key_valid = account_config.api_key_valid
        is_change = self.model.get_hypertts_pro_api_key() != account_config.api_key
        self.model.update_hypertts_pro_config(account_config)
        self.set_cloud_language_tools_enabled()
        if is_change:
            self.model_change()

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

    def disable_all_services(self):
        for service in self.get_service_list():
            checkbox_name = self.get_service_enabled_widget_name(service)
            # find the checkbox
            checkbox = self.dialog.findChild(aqt.qt.QCheckBox, checkbox_name)
            checkbox.setChecked(False)

    def enable_all_free_services(self):
        for service in self.get_service_list():
            if service.service_fee == constants.ServiceFee.Free:
                checkbox_name = self.get_service_enabled_widget_name(service)
                # find the checkbox
                checkbox = self.dialog.findChild(aqt.qt.QCheckBox, checkbox_name)
                checkbox.setChecked(True)

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

        invisible_widget = aqt.qt.QWidget()
        invisible_widget.setVisible(False)


        service_stack = aqt.qt.QWidget(invisible_widget)
        service_vlayout = aqt.qt.QVBoxLayout()
        service_vlayout.setContentsMargins(0, 0, 0, 0)
        if service.cloudlanguagetools_enabled():
            buttons_layout = aqt.qt.QHBoxLayout()
            logo = gui_utils.get_graphic(constants.GRAPHICS_SERVICE_COMPATIBLE)
            buttons_layout.addStretch()
            buttons_layout.addWidget(logo)
            service_vlayout.addLayout(buttons_layout)
        self.draw_service_options(service, service_vlayout)
        service_stack.setLayout(service_vlayout)

        # when cloudlanguagetools is enabled
        # ==================================
        clt_stack = aqt.qt.QWidget(invisible_widget)
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

    def get_service_list(self):
        def service_sort_key(service):
            return service.name
        service_list = self.hypertts.service_manager.get_all_services()
        service_list.sort(key=service_sort_key)
        return service_list


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
        self.hyperttspro.draw(self.global_vlayout)

        # services
        # ========

        def get_separator():
            separator = aqt.qt.QFrame()
            separator.setFrameShape(aqt.qt.QFrame.Shape.HLine)
            separator.setSizePolicy(aqt.qt.QSizePolicy.Policy.Minimum, aqt.qt.QSizePolicy.Policy.Expanding)
            separator.setStyleSheet('color: #cccccc;')
            separator.setLineWidth(2)
            return separator

        self.global_vlayout.addWidget(aqt.qt.QLabel('Services'))
        buttons_layout = aqt.qt.QHBoxLayout()
        self.enable_all_free_services_button = aqt.qt.QPushButton('Enable All Free Services')
        self.disable_all_services_button = aqt.qt.QPushButton('Disable All Services')
        buttons_layout.addWidget(self.enable_all_free_services_button)
        buttons_layout.addWidget(self.disable_all_services_button)
        self.global_vlayout.addLayout(buttons_layout)
        services_scroll_area = ScrollAreaCustom()
        services_scroll_area.setHorizontalScrollBarPolicy(aqt.qt.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        services_scroll_area.setAlignment(aqt.qt.Qt.AlignmentFlag.AlignHCenter)
        services_widget = aqt.qt.QWidget()
        self.services_vlayout = aqt.qt.QVBoxLayout(services_widget)
        
        for service in self.get_service_list():
            self.draw_service(service, self.services_vlayout)
            self.services_vlayout.addWidget(get_separator())

        services_scroll_area.setWidget(services_widget)
        self.global_vlayout.addWidget(services_scroll_area, 1)

        # bottom buttons
        # ==============

        buttons_layout = aqt.qt.QHBoxLayout()
        self.save_button = aqt.qt.QPushButton('Save')
        self.save_button.setEnabled(False)
        self.cancel_button = aqt.qt.QPushButton('Cancel')
        self.cancel_button.setStyleSheet(self.hypertts.anki_utils.get_red_stylesheet())
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        self.global_vlayout.addLayout(buttons_layout)

        # wire events
        # ===========

        self.enable_all_free_services_button.pressed.connect(self.enable_all_free_services)
        self.disable_all_services_button.pressed.connect(self.disable_all_services)

        self.save_button.pressed.connect(self.save_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        # run event once
        # self.pro_api_key_entered()
        self.enable_model_change = True

        layout.addLayout(self.global_vlayout)

    def save_button_pressed(self):
        with self.hypertts.error_manager.get_single_action_context('Saving Service Configuration'):
            self.hypertts.save_configuration(self.model)
            self.hypertts.service_manager.configure(self.model)
            self.dialog.close()

    def cancel_button_pressed(self):
        self.dialog.close()