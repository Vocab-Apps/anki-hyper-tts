import sys
import PyQt5

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)

class BatchSource(component_common.ConfigComponentBase):
    def __init__(self, hypertts, field_list, model_change_callback):
        self.hypertts = hypertts
        self.field_list = field_list
        self.model_change_callback = model_change_callback

        self.batch_source_model = None

    def get_model(self):
        return self.batch_source_model

    def load_model(self, model):
        self.batch_source_model = model
        batch_mode = model.mode
        self.batch_mode_combobox.setCurrentText(batch_mode.name)
        if batch_mode == constants.BatchMode.simple:
            self.source_field_combobox.setCurrentText(model.source_field)
        elif batch_mode == constants.BatchMode.template:
            self.simple_template_input.setText(model.source_template)
        elif batch_mode == constants.BatchMode.advanced_template:
            self.advanced_template_input.setText(model.source_template)


    def draw(self):
        self.batch_source_layout = PyQt5.QtWidgets.QVBoxLayout()

        # batch mode
        self.batch_mode_combobox = PyQt5.QtWidgets.QComboBox()
        self.batch_mode_combobox.addItems([x.name for x in constants.BatchMode])
        self.batch_source_layout.addWidget(self.batch_mode_combobox)

        # source field (for simple mode)
        self.source_field_combobox = PyQt5.QtWidgets.QComboBox()
        self.source_field_combobox.addItems(self.field_list)
        self.batch_source_layout.addWidget(self.source_field_combobox)

        # simple template
        self.simple_template_input = PyQt5.QtWidgets.QLineEdit()
        self.batch_source_layout.addWidget(self.simple_template_input)

        # advanced template
        self.advanced_template_input = PyQt5.QtWidgets.QPlainTextEdit()
        self.batch_source_layout.addWidget(self.advanced_template_input)

        self.batch_source_layout.addStretch()

        # wire events
        self.batch_mode_combobox.currentIndexChanged.connect(self.batch_mode_change)
        self.source_field_combobox.currentIndexChanged.connect(self.source_field_change)
        self.simple_template_input.textChanged.connect(self.simple_template_change)
        self.advanced_template_input.textChanged.connect(self.advanced_template_change)

        # default visibility
        self.simple_template_input.setVisible(False)
        self.advanced_template_input.setVisible(False)        

        # select default
        self.source_field_change(0)

        return self.batch_source_layout

    def batch_mode_change(self, current_index):
        selected_batch_mode = constants.BatchMode[self.batch_mode_combobox.currentText()]

        self.source_field_combobox.setVisible(False)
        self.simple_template_input.setVisible(False)
        self.advanced_template_input.setVisible(False)

        if selected_batch_mode == constants.BatchMode.simple:
            self.source_field_combobox.setVisible(True)
            self.source_field_change(0)
        elif selected_batch_mode == constants.BatchMode.template:
            self.simple_template_input.setVisible(True)
            self.simple_template_change(None)
        elif selected_batch_mode == constants.BatchMode.advanced_template:
            self.advanced_template_change()
            self.advanced_template_input.setVisible(True)

    def source_field_change(self, current_index):
        current_index = self.source_field_combobox.currentIndex()
        field_name = self.field_list[current_index]
        self.batch_source_model = config_models.BatchSourceSimple(field_name)
        self.notify_model_update()

    def simple_template_change(self, simple_template_text):
        simple_template_text = self.simple_template_input.text()
        self.batch_source_model = config_models.BatchSourceTemplate(constants.BatchMode.template, simple_template_text, constants.TemplateFormatVersion.v1)
        self.notify_model_update()

    def advanced_template_change(self):
        template_text = self.advanced_template_input.toPlainText()
        self.batch_source_model = config_models.BatchSourceTemplate(constants.BatchMode.advanced_template, template_text, constants.TemplateFormatVersion.v1)
        self.notify_model_update()

    def notify_model_update(self):
        self.model_change_callback(self.batch_source_model)

    def change_listener(self, note_id, row):
        # logging.info(f'change_listener row {row}')
        self.source_text_preview_table_model.notifyChange(row)
