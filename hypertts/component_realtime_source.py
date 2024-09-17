import sys
import aqt.qt

from . import component_common
from . import constants
from . import config_models
from . import gui_utils
from . import logging_utils
logger = logging_utils.get_child_logger(__name__)

class RealtimeSource(component_common.ConfigComponentBase):
    SOURCE_CONFIG_STACK_ANKITTS = 0

    def __init__(self, hypertts, field_list, model_change_callback):
        self.hypertts = hypertts
        self.field_list = field_list
        self.model_change_callback = model_change_callback

        self.realtime_source_model = None

        # create certain widgets upfront
        self.source_type_combobox = aqt.qt.QComboBox()
        self.source_field_combobox = aqt.qt.QComboBox()
        self.source_field_type_combobox = aqt.qt.QComboBox()        

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
        self.scroll_area = aqt.qt.QScrollArea()
        self.scroll_area.setWidgetResizable(True)        

        self.layout_widget = aqt.qt.QWidget()

        self.realtime_source_layout = aqt.qt.QVBoxLayout(self.layout_widget)

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

        self.scroll_area.setWidget(self.layout_widget)
        return self.scroll_area

    def draw_source_mode(self, overall_layout):
        # batch mode
        groupbox = aqt.qt.QGroupBox('Source Mode')
        vlayout = aqt.qt.QVBoxLayout()
        label = aqt.qt.QLabel(gui_utils.process_label_text(constants.GUI_TEXT_SOURCE_MODE_REALTIME))
        label.setWordWrap(True)
        vlayout.addWidget(label)
        self.source_type_combobox.addItems([x.name for x in constants.RealtimeSourceType])
        vlayout.addWidget(self.source_type_combobox)
        groupbox.setLayout(vlayout)
        overall_layout.addWidget(groupbox)

    def draw_source_config(self, overall_layout):
        groupbox = aqt.qt.QGroupBox('Source Configuration')
        self.source_config_stack = aqt.qt.QStackedWidget()

        ankittstag_stack = aqt.qt.QWidget()

        # simple mode / source field
        # ==========================
        stack_vlayout = aqt.qt.QVBoxLayout()

        # field name
        self.source_field_label = aqt.qt.QLabel(constants.GUI_TEXT_SOURCE_FIELD_NAME)
        self.source_field_combobox.addItems(self.field_list)
        stack_vlayout.addWidget(self.source_field_label)
        stack_vlayout.addWidget(self.source_field_combobox)

        # field type
        self.source_field_type_label = aqt.qt.QLabel(gui_utils.process_label_text(constants.GUI_TEXT_SOURCE_FIELD_TYPE_REALTIME))
        self.source_field_type_label.setWordWrap(True)
        self.source_field_type_combobox.addItems([x.name for x in constants.AnkiTTSFieldType])
        stack_vlayout.addWidget(self.source_field_type_label)
        stack_vlayout.addWidget(self.source_field_type_combobox)

        stack_vlayout.addStretch()
        ankittstag_stack.setLayout(stack_vlayout)

        # finalize stack setup
        # ====================

        self.source_config_stack.addWidget(ankittstag_stack)

        vlayout = aqt.qt.QVBoxLayout()
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

