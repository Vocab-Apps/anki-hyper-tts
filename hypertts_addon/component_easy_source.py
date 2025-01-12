import aqt.qt
from . import component_common
from . import config_models
from . import constants

class ComponentEasySource(component_common.ConfigComponentBase):
    def __init__(self, hypertts, editor_context: config_models.EditorContext, model_change_callback):
        self.hypertts = hypertts
        self.editor_context = editor_context
        self.model_change_callback = model_change_callback
        
        # initialize model
        # self.batch_source_model = config_models.BatchSource(
        #     mode=constants.BatchMode.simple,
        #     source_field=self.editor_context.current_field
        # )
        self.batch_source_model = None

    def draw(self):
        source_group = aqt.qt.QGroupBox('Source Text')
        source_group_layout = aqt.qt.QVBoxLayout()
        source_description_label = aqt.qt.QLabel(constants.GUI_TEXT_EASY_SOURCE_FIELD)
        source_group_layout.addWidget(source_description_label)
        
        self.source_text_edit = aqt.qt.QPlainTextEdit()
        self.source_text_edit.setReadOnly(False)
        self.source_text_edit.setMinimumHeight(50)
        font = self.source_text_edit.font()
        font.setPointSize(20)  # increase font size
        self.source_text_edit.setFont(font)
        self.source_text_edit.setPlainText(self.source_text)
        
        source_group_layout.addWidget(self.source_text_edit)
        source_group.setLayout(source_group_layout)
        
        return source_group

    def update_source_text(self):
        # this function will get the appropriate source text based on the EditorContext
        # the priority should be:
        # - clipboard content if available
        # - selected text if available
        # - current field if available
        # - otherwise, look at whether the source model has a default field
        # - finally, by default, select a field which is populated
        current_field_name = self.editor_context.current_field
        source_text = self.editor_context.note[current_field_name]
        source_text_origin = config_models.SourceTextOrigin.FIELD_TEXT
        return source_text, source_text_origin

    def get_current_text(self):
        return self.source_text_edit.toPlainText()

    def get_model(self):
        return self.batch_source_model

    def load_model(self, model):
        self.batch_source_model = model
        # no UI elements to update since this is just a text editor

    def notify_model_update(self):
        self.model_change_callback(self.batch_source_model)
