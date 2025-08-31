import aqt.qt
from . import component_common
from . import config_models
from . import constants
from . import text_utils
from . import logging_utils

logger = logging_utils.get_child_logger(__name__)

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
            if self.editor_context.note[field_name]:
                preview = trim_preview(self.editor_context.note[field_name])
            else:
                preview = constants.GUI_TEXT_EASY_SOURCE_FIELD_EMPTY
            self.field_combobox.addItem(f"{field_name} ({preview})", field_name)
        source_group_layout.addWidget(self.field_combobox, 0, 1)

        # Add selection option with preview
        if self.editor_context.selected_text:
            self.selection_preview_label.setText(f"({trim_preview(self.editor_context.selected_text)})")
        else:
            self.selection_preview_label.setText(constants.GUI_TEXT_EASY_SOURCE_SELECTION_NO_TEXT)
            self.selection_preview_label.setEnabled(False)
        source_group_layout.addWidget(self.selection_radio, 1, 0)
        source_group_layout.addWidget(self.selection_preview_label, 1, 1)

        # Add clipboard option with preview
        if self.editor_context.clipboard:
            self.clipboard_preview_label.setText(f"({trim_preview(self.editor_context.clipboard)})")
        else:
            self.clipboard_preview_label.setText(constants.GUI_TEXT_EASY_SOURCE_CLIPBOARD_NO_TEXT)
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
        logger.debug(f'editor_context: {self.editor_context}')
        self.clipboard_radio.setEnabled(False)
        self.selection_radio.setEnabled(False)

        # set available options
        if self.editor_context.clipboard:
            logger.debug(f'clipboard enabled: [{self.editor_context.clipboard}]')
            self.clipboard_radio.setEnabled(True)
        if self.editor_context.selected_text:
            logger.debug(f'selection enabled: [{self.editor_context.selected_text}]')
            self.selection_radio.setEnabled(True)            

        # do we have a current field ? (user put the cursor in a field)
        if self.editor_context.current_field:
            logger.debug(f'current_field: {self.editor_context.current_field}')
            field_index = self.field_combobox.findData(self.editor_context.current_field)

            # log full contents of field_combobox
            for i in range(self.field_combobox.count()):
                item_text = self.field_combobox.itemText(i)
                item_data = self.field_combobox.itemData(i)
                logger.debug(f'self.field_combobox: [{i}] text: "{item_text}", data: "{item_data}"')

            if field_index != -1:
                # field data found
                logger.debug(f'found field_index in field_combobox: {field_index}')
                self.field_combobox.setCurrentIndex(field_index)
            else:
                logger.error(f'could not find field in field_combobox')

        # first, check clipboard
        if self.editor_context.clipboard:
            self.field_combobox.setEnabled(False)
            self.clipboard_radio.setChecked(True)
            self.source_text_origin = config_models.SourceTextOrigin.CLIPBOARD
        # next, check selection
        elif self.editor_context.selected_text:
            self.field_combobox.setEnabled(False)
            self.selection_radio.setChecked(True)
            self.source_text_origin = config_models.SourceTextOrigin.SELECTION
        else:
            # default, use field
            self.field_radio.setChecked(True)
            self.field_combobox.setEnabled(True)
            self.source_text_origin = config_models.SourceTextOrigin.FIELD_TEXT
            
        self.update_source_text()

    def update_source_text(self):
        # the user click a radio button change source text
        if self.field_radio.isChecked():
            self.field_combobox.setEnabled(True)
            self.source_text_origin = config_models.SourceTextOrigin.FIELD_TEXT
            current_field = self.field_combobox.currentData()
            source_text = self.editor_context.note[current_field]
            # Clear clipboard if we're moving away from clipboard source
            if self.editor_context.clipboard:
                self.hypertts.anki_utils.clear_clipboard_contents()
        elif self.selection_radio.isChecked():
            self.field_combobox.setEnabled(False)
            self.source_text_origin = config_models.SourceTextOrigin.SELECTION
            source_text = self.editor_context.selected_text
            # Clear clipboard if we're moving away from clipboard source
            if self.editor_context.clipboard:
                self.hypertts.anki_utils.clear_clipboard_contents()
        else:
            self.field_combobox.setEnabled(False)
            self.source_text_origin = config_models.SourceTextOrigin.CLIPBOARD
            source_text = self.editor_context.clipboard

        # process source_text (strip html, etc)
        if source_text != None:
            text_processing_model = config_models.get_easy_mode_source_default_text_processing()
            source_text = text_utils.process_text(source_text, text_processing_model)

        self.source_text_edit.setPlainText(source_text)

        self.build_update_model()
        

    def build_update_model(self):
        current_field = self.field_combobox.currentData()
        # even if the user wants selection or clipboard, we set the model to the currently
        # selected field
        self.batch_source_model = config_models.BatchSource(
            mode=constants.BatchMode.simple, 
            source_field=current_field)

        logger.debug(f'build_update_model: {repr(self.batch_source_model)}')
        self.notify_model_update()

    def get_current_text(self):
        # this should always return the value in self.source_text_edit
        # since the user can enter any text they want
        return self.source_text_edit.toPlainText()


    def get_model(self):
        return self.batch_source_model

    def load_model(self, model):
        self.batch_source_model = model
        
        # if the field name is found in the list of fields, set the combobox to that field
        field_index = self.field_combobox.findData(model.source_field)
        if field_index != -1:
            self.field_combobox.setCurrentIndex(field_index)

    def notify_model_update(self):
        self.model_change_callback(self.batch_source_model)
