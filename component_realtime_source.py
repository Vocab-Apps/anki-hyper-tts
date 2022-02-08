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

        # create certain widgets upfront
        self.source_type_combobox = PyQt5.QtWidgets.QComboBox()
        self.source_field_combobox = PyQt5.QtWidgets.QComboBox()
        self.source_field_type_combobox = PyQt5.QtWidgets.QComboBox()        

    def get_model(self):
        return self.realtime_source_model

    def load_model(self, model):
        self.realtime_source_model = model
        source_type = model.mode
        self.source_type_combobox.setCurrentText(source_type.name)
        if source_type == constants.RealtimeSourceType.AnkiTTSTag:
            self.source_field_combobox.setCurrentText(model.field_name)
            self.source_type_combobox.setCurrentText(model.field_type.name)
        else:
            raise Exception(f'unsupported source_type: {source_type}')


    def draw(self):
        self.realtime_source_layout = PyQt5.QtWidgets.QVBoxLayout()

        self.draw_source_mode(self.realtime_source_layout)
        self.draw_source_config(self.realtime_source_layout)
        self.realtime_source_layout.addStretch()

        # wire events
        self.source_type_combobox.currentIndexChanged.connect(self.source_type_change)
        self.source_field_combobox.currentIndexChanged.connect(self.source_field_change)
        self.source_field_type_combobox.currentIndexChanged.connect(self.field_type_change)

        # select default
        self.source_type_change(0)
        self.source_field_change(0)
        self.field_type_change(0)


        return self.realtime_source_layout

    def draw_source_mode(self, overall_layout):
        # batch mode
        groupbox = PyQt5.QtWidgets.QGroupBox('Source Mode')
        vlayout = PyQt5.QtWidgets.QVBoxLayout()
        label = PyQt5.QtWidgets.QLabel(gui_utils.process_label_text(constants.GUI_TEXT_SOURCE_MODE_REALTIME))
        label.setWordWrap(True)
        vlayout.addWidget(label)
        self.source_type_combobox.addItems([x.name for x in constants.RealtimeSourceType])
        vlayout.addWidget(self.source_type_combobox)
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
        self.source_field_combobox.addItems(self.field_list)
        stack_vlayout.addWidget(self.source_field_label)
        stack_vlayout.addWidget(self.source_field_combobox)

        # field type
        self.source_field_type_label = PyQt5.QtWidgets.QLabel(gui_utils.process_label_text(constants.GUI_TEXT_SOURCE_FIELD_TYPE_REALTIME))
        self.source_field_type_label.setWordWrap(True)
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

    def source_type_change(self, current_index):
        selected_source_type = constants.RealtimeSourceType[self.source_type_combobox.currentText()]

        if selected_source_type == constants.RealtimeSourceType.AnkiTTSTag:
            self.source_config_stack.setCurrentIndex(self.SOURCE_CONFIG_STACK_ANKITTS)
            self.realtime_source_model = config_models.RealtimeSourceAnkiTTS()
            self.source_field_change(0)
        else:
            raise Exception(f'unsupported source_type: {selected_source_type}')

    def source_field_change(self, current_index):
        current_index = self.source_field_combobox.currentIndex()
        field_name = self.field_list[current_index]
        self.realtime_source_model.field_name = field_name
        self.notify_model_update()

    def field_type_change(self, current_index):
        field_type = constants.AnkiTTSFieldType[self.source_field_type_combobox.currentText()]
        self.realtime_source_model.field_type = field_type
        self.notify_model_update()        

    def notify_model_update(self):
        self.model_change_callback(self.realtime_source_model)

