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
        if batch_mode == constants.RealtimeSourceType.simple:
            self.source_field_combobox.setCurrentText(model.source_field)
        elif batch_mode == constants.RealtimeSourceType.template:
            self.simple_template_input.setText(model.source_template)
        elif batch_mode == constants.RealtimeSourceType.advanced_template:
            self.advanced_template_input.setPlainText(model.source_template)


    def draw(self):
        self.batch_source_layout = PyQt5.QtWidgets.QVBoxLayout()

        self.draw_source_mode(self.batch_source_layout)
        self.draw_source_config(self.batch_source_layout)
        # self.batch_source_layout.addStretch()

        # wire events
        self.batch_mode_combobox.currentIndexChanged.connect(self.batch_mode_change)
        self.source_field_combobox.currentIndexChanged.connect(self.source_field_change)

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

        ankittstag_stack = PyQt5.QtWidgets.QWidget()

        # simple mode / source field
        # ==========================
        stack_vlayout = PyQt5.QtWidgets.QVBoxLayout()

        # field name
        self.source_field_label = PyQt5.QtWidgets.QLabel(constants.GUI_TEXT_SOURCE_FIELD_NAME)
        self.source_field_combobox = PyQt5.QtWidgets.QComboBox()
        self.source_field_combobox.addItems(self.field_list)
        stack_vlayout.addWidget(self.source_field_label)
        stack_vlayout.addWidget(self.source_field_combobox)

        # field type
        self.source_field_type_label = PyQt5.QtWidgets.QLabel(gui_utils.process_label_text(constants.GUI_TEXT_SOURCE_FIELD_TYPE_REALTIME))
        self.source_field_type_label.setWordWrap(True)
        self.source_field_type_combobox = PyQt5.QtWidgets.QComboBox()
        self.source_field_type_combobox.addItems([x.name for x in constants.AnkiTTSFieldType])
        stack_vlayout.addWidget(self.source_field_type_label)
        stack_vlayout.addWidget(self.source_field_type_combobox)

        stack_vlayout.addStretch()
        ankittstag_stack.setLayout(stack_vlayout)

        # finalize stack setup
        # ====================

        self.source_config_stack.addWidget(ankittstag_stack)

        vlayout = PyQt5.QtWidgets.QVBoxLayout()
        vlayout.addWidget(self.source_config_stack)
        groupbox.setLayout(vlayout)

        overall_layout.addWidget(groupbox)

    def batch_mode_change(self, current_index):
        selected_batch_mode = constants.BatchMode[self.batch_mode_combobox.currentText()]

        if selected_batch_mode == constants.RealtimeSourceType.AnkiTTSTag:
            self.source_config_stack.setCurrentIndex(self.SOURCE_CONFIG_STACK_ANKITTS)
            self.source_field_change(0)

    def source_field_change(self, current_index):
        current_index = self.source_field_combobox.currentIndex()
        field_name = self.field_list[current_index]
        self.realtime_source_model = config_models.BatchSourceSimple(field_name)
        self.notify_model_update()

    def notify_model_update(self):
        self.model_change_callback(self.realtime_source_model)

