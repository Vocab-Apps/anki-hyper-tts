import aqt.qt
from . import component_common
from . import config_models
from . import constants

MAX_PREVIEW_CHARACTERS = 20

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
        self.selection_preview_label = aqt.qt.QLabel()
        self.clipboard_preview_label = aqt.qt.QLabel()

    def draw(self):
        def trim_preview(text):
            """Trim text to 20 chars and add ellipsis if needed"""
            if len(text) > MAX_PREVIEW_CHARACTERS:
                return text[:MAX_PREVIEW_CHARACTERS] + '...'
            return text

        source_group = aqt.qt.QGroupBox('Source Text')
        source_group_layout = aqt.qt.QGridLayout()
        
        # source origin controls
        # ======================

        # Add field selection controls
        source_group_layout.addWidget(self.field_radio, 0, 0)
        # populate combobox with field names and preview text
        for field_name in self.editor_context.note.keys():
            preview = trim_preview(self.editor_context.note[field_name])
            self.field_combobox.addItem(f"{field_name} ({preview})", field_name)
        source_group_layout.addWidget(self.field_combobox, 0, 1)

        # Add selection option with preview
        if self.editor_context.selected_text:
            self.selection_preview_label.setText(f"({trim_preview(self.editor_context.selected_text)})")
        else:
            self.selection_preview_label.setText('<i>(no selected text)</i>')
            self.selection_preview_label.setEnabled(False)
        source_group_layout.addWidget(self.selection_radio, 1, 0)
        source_group_layout.addWidget(self.selection_preview_label, 1, 1)

        # Add clipboard option with preview
        if self.editor_context.clipboard:
            self.clipboard_preview_label.setText(f"({trim_preview(self.editor_context.clipboard)})")
        else:
            self.clipboard_preview_label.setText("<i>(no clipboard text)</i>")
            self.clipboard_preview_label.setEnabled(False)
        source_group_layout.addWidget(self.clipboard_radio, 2, 0)
        source_group_layout.addWidget(self.clipboard_preview_label, 2, 1)
        
        # disable options if not available
        if not self.editor_context.selected_text:
            self.selection_radio.setEnabled(False)
        if not self.editor_context.clipboard:
            self.clipboard_radio.setEnabled(False)
        
        # text preview
        # ============

        self.source_text_edit = aqt.qt.QPlainTextEdit()
        # self.source_text_edit should not be readonly, the user can enter any value 
        # they want in there.
        self.source_text_edit.setMinimumHeight(50)
        font = self.source_text_edit.font()
        font.setPointSize(20)
        self.source_text_edit.setFont(font)
        
        source_group_layout.addWidget(self.source_text_edit, 3, 0, 1, 2)
        
        # Make second column expand
        source_group_layout.setColumnStretch(1, 1)
        
        source_group.setLayout(source_group_layout)

        # wire up events
        self.field_radio.toggled.connect(self.update_source_text)
        self.selection_radio.toggled.connect(self.update_source_text)
        self.clipboard_radio.toggled.connect(self.update_source_text)
        self.field_combobox.currentIndexChanged.connect(self.update_source_text)
        
        # set initial state
        self.update_source_text_initial_options()
        
        return source_group

    def update_source_text_initial_options(self):
        self.clipboard_radio.setEnabled(False)
        self.selection_radio.setEnabled(False)

        # set available options
        if self.editor_context.clipboard:
            self.clipboard_radio.setEnabled(True)
        if self.editor_context.selected_text:
            self.selection_radio.setEnabled(True)            

        # first, check clipboard
        if self.editor_context.clipboard:
            self.clipboard_radio.setChecked(True)
            self.source_text_origin = config_models.SourceTextOrigin.CLIPBOARD
            source_text = self.editor_context.clipboard
        # next, check selection
        elif self.editor_context.selected_text:
            self.selection_radio.setChecked(True)
            self.source_text_origin = config_models.SourceTextOrigin.SELECTION
            source_text = self.editor_context.selected_text
        else:
            # default, use field
            self.field_radio.setChecked(True)
            self.source_text_origin = config_models.SourceTextOrigin.FIELD_TEXT
            current_field = self.field_combobox.currentData()
            source_text = self.editor_context.note[current_field]
            
        self.source_text_edit.setPlainText(source_text)
        self.notify_model_update()

    def update_source_text(self):
        # the user click a radio button change source text
        if self.field_radio.isChecked():
            self.source_text_origin = config_models.SourceTextOrigin.FIELD_TEXT
            current_field = self.field_combobox.currentData()
            source_text = self.editor_context.note[current_field]
        elif self.selection_radio.isChecked():
            self.source_text_origin = config_models.SourceTextOrigin.SELECTION
            source_text = self.editor_context.selected_text
        else:
            self.source_text_origin = config_models.SourceTextOrigin.CLIPBOARD
            source_text = self.editor_context.clipboard
        self.source_text_edit.setPlainText(source_text)
        self.notify_model_update()


    def get_current_text(self):
        # this should always return the value in self.source_text_edit
        # since the user can enter any text they want
        return self.source_text_edit.toPlainText()


    def get_model(self):
        return self.batch_source_model

    def load_model(self, model):
        self.batch_source_model = model
        # no UI elements to update since this is just a text editor

    def notify_model_update(self):
        self.model_change_callback(self.batch_source_model)
