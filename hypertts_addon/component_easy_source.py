import aqt.qt
from . import component_common
from . import config_models
from . import constants

class ComponentEasySource(component_common.ConfigComponentBase):
    def __init__(self, hypertts, editor_context: config_models.EditorContext, model_change_callback):
        self.hypertts = hypertts
        self.editor_context = editor_context
        self.model_change_callback = model_change_callback
        
        self.batch_source_model = None
        self.source_text_origin = config_models.SourceTextOrigin.FIELD_TEXT

        # initialize widgets
        self.field_radio = aqt.qt.QRadioButton(config_models.SourceTextOrigin.FIELD_TEXT.description)
        self.selection_radio = aqt.qt.QRadioButton(config_models.SourceTextOrigin.SELECTION.description)
        self.clipboard_radio = aqt.qt.QRadioButton(config_models.SourceTextOrigin.CLIPBOARD.description)
        self.field_combobox = aqt.qt.QComboBox()

    def draw(self):
        source_group = aqt.qt.QGroupBox('Source Text')
        source_group_layout = aqt.qt.QVBoxLayout()
        
        # radio button group
        radio_layout = aqt.qt.QVBoxLayout()
        
        # field selection row
        field_layout = aqt.qt.QHBoxLayout()
        field_layout.addWidget(self.field_radio)
        self.field_combobox.addItems(self.editor_context.note.keys())
        field_layout.addWidget(self.field_combobox)
        radio_layout.addLayout(field_layout)
        
        # selection and clipboard options
        radio_layout.addWidget(self.selection_radio)
        radio_layout.addWidget(self.clipboard_radio)
        
        # disable options if not available
        if not self.editor_context.selected_text:
            self.selection_radio.setEnabled(False)
        if not self.editor_context.clipboard:
            self.clipboard_radio.setEnabled(False)
            
        source_group_layout.addLayout(radio_layout)
        
        # text preview
        self.source_text_edit = aqt.qt.QPlainTextEdit()
        self.source_text_edit.setReadOnly(True)
        self.source_text_edit.setMinimumHeight(50)
        font = self.source_text_edit.font()
        font.setPointSize(20)
        self.source_text_edit.setFont(font)
        
        source_group_layout.addWidget(self.source_text_edit)
        source_group.setLayout(source_group_layout)

        # wire up events
        self.field_radio.toggled.connect(self.update_source_text)
        self.selection_radio.toggled.connect(self.update_source_text)
        self.clipboard_radio.toggled.connect(self.update_source_text)
        self.field_combobox.currentIndexChanged.connect(self.update_source_text)
        
        # set initial state
        self.field_radio.setChecked(True)
        self.update_source_text()
        
        return source_group

    def update_source_text(self):
        if self.field_radio.isChecked():
            self.source_text_origin = config_models.SourceTextOrigin.FIELD_TEXT
            current_field = self.field_combobox.currentText()
            source_text = self.editor_context.note[current_field]
        elif self.selection_radio.isChecked():
            self.source_text_origin = config_models.SourceTextOrigin.SELECTION
            source_text = self.editor_context.selected_text
        elif self.clipboard_radio.isChecked():
            self.source_text_origin = config_models.SourceTextOrigin.CLIPBOARD
            source_text = self.editor_context.clipboard
        else:
            source_text = ""
            
        self.source_text_edit.setPlainText(source_text)
        self.notify_model_update()

    def get_current_text(self):
        if self.field_radio.isChecked():
            return self.editor_context.note[self.field_combobox.currentText()]
        elif self.selection_radio.isChecked():
            return self.editor_context.selected_text
        elif self.clipboard_radio.isChecked():
            return self.editor_context.clipboard
        return ""

    def get_model(self):
        return self.batch_source_model

    def load_model(self, model):
        self.batch_source_model = model
        # no UI elements to update since this is just a text editor

    def notify_model_update(self):
        self.model_change_callback(self.batch_source_model)
