import aqt.qt
from . import component_common
from . import config_models
from . import constants

class ComponentEasySource(component_common.ComponentBase):
    def __init__(self, hypertts, editor_context: config_models.EditorContext, source_text_updated_fn):
        self.hypertts = hypertts
        self.editor_context = editor_context
        self.source_text_updated_fn = source_text_updated_fn
        
        # get initial source text
        self.source_text, self.source_text_origin = self.get_source_text()

    def get_source_text(self):
        current_field_name = self.editor_context.current_field
        source_text = self.editor_context.note[current_field_name]
        source_text_origin = config_models.SourceTextOrigin.FIELD_TEXT
        return source_text, source_text_origin

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

    def get_source_text(self):
        return self.source_text
