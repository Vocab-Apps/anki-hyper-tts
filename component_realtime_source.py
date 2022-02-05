import sys
import PyQt5

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
gui_utils = __import__('gui_utils', globals(), locals(), [], sys._addon_import_level_base)

class RealtimeSource(component_common.ConfigComponentBase):
    SOURCE_CONFIG_STACK_ANKITTS = 0

    def __init__(self, hypertts, field_list, model_change_callback):
        self.hypertts = hypertts
        self.field_list = field_list
        self.model_change_callback = model_change_callback

        self.realtime_source_model = None

    def get_model(self):
        return self.realtime_source_model

    def load_model(self, model):
        self.realtime_source_model = model
        batch_mode = model.mode
        self.batch_mode_combobox.setCurrentText(batch_mode.name)
        if batch_mode == constants.BatchMode.simple:
            self.source_field_combobox.setCurrentText(model.source_field)
        elif batch_mode == constants.BatchMode.template:
            self.simple_template_input.setText(model.source_template)
        elif batch_mode == constants.BatchMode.advanced_template:
            self.advanced_template_input.setPlainText(model.source_template)


    def draw(self):
        self.batch_source_layout = PyQt5.QtWidgets.QVBoxLayout()

        self.draw_source_mode(self.batch_source_layout)
        self.draw_source_config(self.batch_source_layout)
        # self.batch_source_layout.addStretch()

        # wire events
        self.batch_mode_combobox.currentIndexChanged.connect(self.batch_mode_change)
        self.source_field_combobox.currentIndexChanged.connect(self.source_field_change)
        self.hypertts.anki_utils.wire_typing_timer(self.simple_template_input, self.simple_template_change)
        self.hypertts.anki_utils.wire_typing_timer(self.advanced_template_input, self.advanced_template_change)

        # select default
        self.source_field_change(0)

        return self.batch_source_layout

    def draw_source_mode(self, overall_layout):
        # batch mode
        groupbox = PyQt5.QtWidgets.QGroupBox('Source Mode')
        vlayout = PyQt5.QtWidgets.QVBoxLayout()
        label = PyQt5.QtWidgets.QLabel(gui_utils.process_label_text(constants.GUI_TEXT_SOURCE_MODE_REALTIME))
        label.setWordWrap(True)
        vlayout.addWidget(label)
        self.batch_mode_combobox = PyQt5.QtWidgets.QComboBox()
        self.batch_mode_combobox.addItems([x.name for x in constants.RealtimeSourceType])
        vlayout.addWidget(self.batch_mode_combobox)
        groupbox.setLayout(vlayout)
        overall_layout.addWidget(groupbox)

    def draw_source_config(self, overall_layout):
        groupbox = PyQt5.QtWidgets.QGroupBox('Source Configuration')
        self.source_config_stack = PyQt5.QtWidgets.QStackedWidget()

        simple_stack = PyQt5.QtWidgets.QWidget()
        template_stack = PyQt5.QtWidgets.QWidget()
        advanced_template_stack = PyQt5.QtWidgets.QWidget()

        # simple mode / source field
        # ==========================
        stack_vlayout = PyQt5.QtWidgets.QVBoxLayout()
        self.source_field_label = PyQt5.QtWidgets.QLabel(constants.GUI_TEXT_SOURCE_FIELD_NAME)
        self.source_field_combobox = PyQt5.QtWidgets.QComboBox()
        self.source_field_combobox.addItems(self.field_list)
        stack_vlayout.addWidget(self.source_field_label)
        stack_vlayout.addWidget(self.source_field_combobox)
        stack_vlayout.addStretch()
        simple_stack.setLayout(stack_vlayout)

        # simple template 
        # ===============
        stack_vlayout = PyQt5.QtWidgets.QVBoxLayout()
        label = PyQt5.QtWidgets.QLabel(constants.GUI_TEXT_SOURCE_SIMPLE_TEMPLATE)
        label.setTextInteractionFlags(PyQt5.QtCore.Qt.TextSelectableByMouse)
        self.simple_template_input = PyQt5.QtWidgets.QLineEdit()
        stack_vlayout.addWidget(label)
        stack_vlayout.addWidget(self.simple_template_input)
        stack_vlayout.addStretch()
        template_stack.setLayout(stack_vlayout)

        # advanced template
        # =================
        stack_vlayout = PyQt5.QtWidgets.QVBoxLayout()
        label = PyQt5.QtWidgets.QLabel(constants.GUI_TEXT_SOURCE_ADVANCED_TEMPLATE)
        label.setTextInteractionFlags(PyQt5.QtCore.Qt.TextSelectableByMouse)
        self.advanced_template_input = PyQt5.QtWidgets.QPlainTextEdit()
        stack_vlayout.addWidget(label)
        stack_vlayout.addWidget(self.advanced_template_input)
        stack_vlayout.addStretch()
        advanced_template_stack.setLayout(stack_vlayout)

        # finalize stack setup
        # ====================

        self.source_config_stack.addWidget(simple_stack)
        self.source_config_stack.addWidget(template_stack)
        self.source_config_stack.addWidget(advanced_template_stack)

        vlayout = PyQt5.QtWidgets.QVBoxLayout()
        vlayout.addWidget(self.source_config_stack)
        groupbox.setLayout(vlayout)

        overall_layout.addWidget(groupbox)

    def batch_mode_change(self, current_index):
        selected_batch_mode = constants.BatchMode[self.batch_mode_combobox.currentText()]

        if selected_batch_mode == constants.BatchMode.simple:
            self.source_config_stack.setCurrentIndex(self.SOURCE_CONFIG_STACK_SIMPLE)
            self.source_field_change(0)
        elif selected_batch_mode == constants.BatchMode.template:
            self.source_config_stack.setCurrentIndex(self.SOURCE_CONFIG_STACK_TEMPLATE)
            self.simple_template_change(None)
        elif selected_batch_mode == constants.BatchMode.advanced_template:
            self.source_config_stack.setCurrentIndex(self.SOURCE_CONFIG_STACK_ADVANCED_TEMPLATE)
            self.advanced_template_change()

    def source_field_change(self, current_index):
        current_index = self.source_field_combobox.currentIndex()
        field_name = self.field_list[current_index]
        self.realtime_source_model = config_models.BatchSourceSimple(field_name)
        self.notify_model_update()

    def simple_template_change(self, simple_template_text):
        simple_template_text = self.simple_template_input.text()
        self.realtime_source_model = config_models.BatchSourceTemplate(constants.BatchMode.template, simple_template_text, constants.TemplateFormatVersion.v1)
        self.notify_model_update()

    def advanced_template_change(self):
        template_text = self.advanced_template_input.toPlainText()
        self.realtime_source_model = config_models.BatchSourceTemplate(constants.BatchMode.advanced_template, template_text, constants.TemplateFormatVersion.v1)
        self.notify_model_update()

    def notify_model_update(self):
        self.model_change_callback(self.realtime_source_model)

