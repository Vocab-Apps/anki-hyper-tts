import sys
import aqt.qt
import pprint

from . import component_common
from . import constants
from . import config_models
from . import gui_utils
from . import logging_utils
logger = logging_utils.get_child_logger(__name__)

class BatchSource(component_common.ConfigComponentBase):
    SOURCE_CONFIG_STACK_SIMPLE = 0
    SOURCE_CONFIG_STACK_TEMPLATE = 1
    SOURCE_CONFIG_STACK_ADVANCED_TEMPLATE = 2

    def __init__(self, hypertts, field_list, model_change_callback):
        self.hypertts = hypertts
        self.field_list = field_list
        self.model_change_callback = model_change_callback

        self.batch_source_model = None
        self.events_enabled = True

    def get_model(self):
        return self.batch_source_model

    def load_model(self, model):
        logger.debug('load_model')
        self.disconnect_events()

        self.batch_source_model = model
        batch_mode = model.mode
        self.batch_mode_combobox.setCurrentText(batch_mode.name)
        if batch_mode == constants.BatchMode.simple:
            self.source_field_combobox.setCurrentText(model.source_field)
            self.use_selection_checkbox.setChecked(model.use_selection)
        elif batch_mode == constants.BatchMode.template:
            self.simple_template_input.setText(model.source_template)
        elif batch_mode == constants.BatchMode.advanced_template:
            self.advanced_template_input.setPlainText(model.source_template)

        self.wire_events()


    def draw(self): # return a widget

        self.scroll_area = aqt.qt.QScrollArea()
        self.scroll_area.setWidgetResizable(True)        

        self.layout_widget = aqt.qt.QWidget()
        self.batch_source_layout = aqt.qt.QVBoxLayout(self.layout_widget)

        self.draw_source_mode(self.batch_source_layout)
        self.draw_source_config(self.batch_source_layout)
        self.batch_source_layout.addStretch()

        # wire events
        self.batch_mode_combobox.currentIndexChanged.connect(self.batch_mode_change)
        self.source_field_combobox.currentIndexChanged.connect(self.source_field_change)
        self.use_selection_checkbox.stateChanged.connect(self.use_selection_checkbox_change)
        self.simple_template_typing_timer = self.hypertts.anki_utils.wire_typing_timer(self.simple_template_input, self.simple_template_change)
        self.advanced_template_typing_timer = self.hypertts.anki_utils.wire_typing_timer(self.advanced_template_input, self.advanced_template_change)

        # select default
        self.source_field_change(0)

        # return self.batch_source_layout
        
        self.scroll_area.setWidget(self.layout_widget)
        return self.scroll_area

    def disable_typing_timers(self):
        logger.debug('disable_typing_timers')
        self.simple_template_typing_timer.enabled = False
        self.advanced_template_typing_timer.enabled = False

    def enable_typing_timers(self):
        logger.debug('enable_typing_timers')
        self.simple_template_typing_timer.enabled = True
        self.advanced_template_typing_timer.enabled = True

    def wire_events(self):
        logger.debug('wire_events')
        self.events_enabled = True
        self.enable_typing_timers()


    def disconnect_events(self):
        logger.debug('disconnect_events')
        self.events_enabled = False
        self.disable_typing_timers()

    def draw_source_mode(self, overall_layout):
        # batch mode
        groupbox = aqt.qt.QGroupBox('Source Mode')
        vlayout = aqt.qt.QVBoxLayout()
        label = aqt.qt.QLabel(gui_utils.process_label_text(constants.GUI_TEXT_SOURCE_MODE))
        label.setWordWrap(True)
        vlayout.addWidget(label)
        self.batch_mode_combobox = aqt.qt.QComboBox()
        self.batch_mode_combobox.addItems([x.name for x in constants.BatchMode])
        vlayout.addWidget(self.batch_mode_combobox)
        groupbox.setLayout(vlayout)
        overall_layout.addWidget(groupbox)

    def draw_source_config(self, overall_layout):
        groupbox = aqt.qt.QGroupBox('Source Configuration')
        self.source_config_stack = aqt.qt.QStackedWidget()

        simple_stack = aqt.qt.QWidget()
        template_stack = aqt.qt.QWidget()
        advanced_template_stack = aqt.qt.QWidget()

        # simple mode / source field
        # ==========================
        stack_vlayout = aqt.qt.QVBoxLayout()
        self.source_field_label = aqt.qt.QLabel(constants.GUI_TEXT_SOURCE_FIELD_NAME)
        self.source_field_combobox = aqt.qt.QComboBox()
        self.source_field_combobox.addItems(self.field_list)
        stack_vlayout.addWidget(self.source_field_label)
        stack_vlayout.addWidget(self.source_field_combobox)
        self.use_selection_checkbox = aqt.qt.QCheckBox(constants.GUI_TEXT_SOURCE_USE_SELECTION)
        stack_vlayout.addWidget(aqt.qt.QLabel('Additional Settings:'))
        stack_vlayout.addWidget(self.use_selection_checkbox)
        stack_vlayout.addStretch()
        simple_stack.setLayout(stack_vlayout)

        # simple template 
        # ===============
        stack_vlayout = aqt.qt.QVBoxLayout()
        label = aqt.qt.QLabel(constants.GUI_TEXT_SOURCE_SIMPLE_TEMPLATE)
        label.setTextInteractionFlags(aqt.qt.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.simple_template_input = aqt.qt.QLineEdit()
        stack_vlayout.addWidget(label)
        stack_vlayout.addWidget(self.simple_template_input)
        stack_vlayout.addStretch()
        template_stack.setLayout(stack_vlayout)

        # advanced template
        # =================
        stack_vlayout = aqt.qt.QVBoxLayout()
        label = aqt.qt.QLabel(constants.GUI_TEXT_SOURCE_ADVANCED_TEMPLATE)
        label.setTextInteractionFlags(aqt.qt.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.advanced_template_input = aqt.qt.QPlainTextEdit()
        stack_vlayout.addWidget(label)
        stack_vlayout.addWidget(self.advanced_template_input)
        stack_vlayout.addStretch()
        advanced_template_stack.setLayout(stack_vlayout)

        # finalize stack setup
        # ====================

        self.source_config_stack.addWidget(simple_stack)
        self.source_config_stack.addWidget(template_stack)
        self.source_config_stack.addWidget(advanced_template_stack)

        vlayout = aqt.qt.QVBoxLayout()
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
            self.simple_template_change()
        elif selected_batch_mode == constants.BatchMode.advanced_template:
            self.source_config_stack.setCurrentIndex(self.SOURCE_CONFIG_STACK_ADVANCED_TEMPLATE)
            self.advanced_template_change()

    def source_field_change(self, current_index):
        current_index = self.source_field_combobox.currentIndex()
        if current_index == -1 or current_index >= len(self.field_list) or len(self.field_list) == 0:
            error_message = f'current_index for source_field_combobox is {current_index}, field_list: {self.field_list}'
            raise Exception(error_message)
        field_name = self.field_list[current_index]
        self.batch_source_model = config_models.BatchSource(mode=constants.BatchMode.simple, source_field=field_name)
        self.notify_model_update()

    def use_selection_checkbox_change(self):
        use_selection = self.use_selection_checkbox.isChecked()
        self.batch_source_model.use_selection = use_selection
        self.notify_model_update()

    def simple_template_change(self):
        if not self.events_enabled:
            return
        logger.debug('simple_template_change')
        simple_template_text = self.simple_template_input.text()
        self.batch_source_model = config_models.BatchSource(mode=constants.BatchMode.template, source_template=simple_template_text)
        self.notify_model_update()

    def advanced_template_change(self):
        if not self.events_enabled:
            return
        logger.debug('advanced_template_change')
        template_text = self.advanced_template_input.toPlainText()
        self.batch_source_model = config_models.BatchSource(mode=constants.BatchMode.advanced_template, source_template=template_text)
        self.notify_model_update()

    def notify_model_update(self):
        self.model_change_callback(self.batch_source_model)

    def change_listener(self, note_id, row):
        # logger.info(f'change_listener row {row}')
        self.source_text_preview_table_model.notifyChange(row)
