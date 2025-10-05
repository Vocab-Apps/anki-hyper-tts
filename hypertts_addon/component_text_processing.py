import sys
import aqt.qt
import html

from . import constants
from . import component_common
from . import config_models
from . import gui_utils
from . import text_utils
from . import logging_utils
logger = logging_utils.get_child_logger(__name__)


class TextProcessing(component_common.ConfigComponentBase):
    def __init__(self, hypertts, model_change_callback):
        self.hypertts = hypertts
        self.model_change_callback = model_change_callback

COL_INDEX_TYPE = 0
COL_INDEX_PATTERN = 1
COL_INDEX_REPLACEMENT = 2

BLANK_TEXT = '<i>Enter sample text to verify text processing settings.</i>'

class TextReplacementsTableModel(aqt.qt.QAbstractTableModel):
    def __init__(self, model, model_change_callback):
        aqt.qt.QAbstractTableModel.__init__(self, None)

        self.model = model
        self.model_change_callback = model_change_callback

        self.header_text = [
            'Type',
            'Pattern',
            'Replacement'
        ]

    def load_model(self, model):
        self.model = model
        logger.info(model)
        self.layoutChanged.emit()

    def flags(self, index):
        # all columns are editable
        col = index.column()
        if col == COL_INDEX_TYPE:
            # not editable
            return aqt.qt.Qt.ItemFlag.ItemIsSelectable | aqt.qt.Qt.ItemFlag.ItemIsEnabled
        if col == COL_INDEX_PATTERN or col == COL_INDEX_REPLACEMENT:
            return aqt.qt.Qt.ItemFlag.ItemIsEditable | aqt.qt.Qt.ItemFlag.ItemIsSelectable | aqt.qt.Qt.ItemFlag.ItemIsEnabled
        logger.warning(f'unknown column: {col}')
        return aqt.qt.Qt.ItemFlag.ItemIsSelectable | aqt.qt.Qt.ItemFlag.ItemIsEnabled


    def rowCount(self, parent):
        return len(self.model.text_replacement_rules)

    def columnCount(self, parent):
        return self.num_columns()

    def num_columns(self):
        return len(self.header_text)

    def add_replacement(self, replace_type):
        self.model.add_text_replacement_rule(config_models.TextReplacementRule(replace_type))
        self.layoutChanged.emit()
        self.model_change_callback()

    def delete_rows(self, row_index):
        row = row_index.row()
        if row >= len(self.model.text_replacement_rules):
            logger.error(f'num replacement rules: {len(self.model.text_replacement_rules)} row: {row}, cannot delete rows')
            return

        self.model.remove_text_replacement_rule(row)
        self.layoutChanged.emit()
        self.model_change_callback()        

    def data(self, index, role):
        if not index.isValid():
            return aqt.qt.QVariant()

        column = index.column()
        row = index.row()

        # check whether we've got data for this row
        if row >= len(self.model.text_replacement_rules):
            return aqt.qt.QVariant()

        text_replacement_rule = self.model.get_text_replacement_rule_row(row)

        if role == aqt.qt.Qt.ItemDataRole.DisplayRole or role == aqt.qt.Qt.ItemDataRole.EditRole:

            if column == COL_INDEX_TYPE:
                return aqt.qt.QVariant(text_replacement_rule.rule_type.name.title())
            if column == COL_INDEX_PATTERN:
                return self.data_display(text_replacement_rule.source, role)
            if column == COL_INDEX_REPLACEMENT:
                return self.data_display(text_replacement_rule.target, role)

        return aqt.qt.QVariant()

    def data_display(self, value, role):
        if role == aqt.qt.Qt.ItemDataRole.DisplayRole:
            text = '""'
            if value != None:
                text = '"' + value + '"'
            return aqt.qt.QVariant(text)
        elif role == aqt.qt.Qt.ItemDataRole.EditRole:
            return aqt.qt.QVariant(value)

    def setData(self, index, value, role):
        if not index.isValid():
            return False

        column = index.column()
        row = index.row()

        if row >= len(self.model.get_text_replacement_rules()):
            logger.error(f'setData column {column} row {row}, num rules: {len(self.model.get_text_replacement_rules())}')
            return False

        text_replacement_rule = self.model.get_text_replacement_rule_row(row)

        if role == aqt.qt.Qt.ItemDataRole.EditRole:
            
            # set the value into a TextReplacement object
            if column == COL_INDEX_TYPE:
                # editing no supported
                return False
            elif column == COL_INDEX_PATTERN:
                text_replacement_rule.source = value
            elif column == COL_INDEX_REPLACEMENT:
                text_replacement_rule.target = value

            # emit change signal
            start_index = self.createIndex(row, column)
            end_index = self.createIndex(row, column)
            self.dataChanged.emit(start_index, end_index)
            self.model_change_callback()
            return True

        else:
            return False

    def headerData(self, col, orientation, role):
        if orientation == aqt.qt.Qt.Orientation.Horizontal and role == aqt.qt.Qt.ItemDataRole.DisplayRole:
            return aqt.qt.QVariant(self.header_text[col])
        return aqt.qt.QVariant()

class TextProcessing(component_common.ConfigComponentBase):
    def __init__(self, hypertts, model_change_callback):
        self.hypertts = hypertts
        self.model_change_callback = model_change_callback
        self.model = config_models.TextProcessing()
        self.textReplacementTableModel = TextReplacementsTableModel(self.model, self.model_change)

    def get_model(self):
        return self.model

    def load_model(self, model):
        logger.info(f'load_model')
        self.model = model
        self.textReplacementTableModel.load_model(self.model)
        self.set_text_processing_rules_widget_state()

    def draw(self): # return scrollarea
        self.scroll_area = aqt.qt.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.layout_widget = aqt.qt.QWidget()        

        global_vlayout = aqt.qt.QVBoxLayout(self.layout_widget)


        # setup test input box
        # ====================

        groupbox = aqt.qt.QGroupBox('Preview Text Processing Settings')
        vlayout = aqt.qt.QVBoxLayout()

        vlayout.addWidget(aqt.qt.QLabel('You may verify your settings by entering sample text below:'))

        # first line
        hlayout = aqt.qt.QHBoxLayout()
        label = aqt.qt.QLabel('Enter sample text:')
        hlayout.addWidget(label)
        self.sample_text_input = aqt.qt.QLineEdit()
        hlayout.addWidget(self.sample_text_input)
        hlayout.addStretch()
        vlayout.addLayout(hlayout)

        # second line
        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addWidget(aqt.qt.QLabel('Transformed Text:'))
        self.sample_text_transformed_label = aqt.qt.QLabel(BLANK_TEXT)
        hlayout.addWidget(self.sample_text_transformed_label)
        hlayout.addStretch()
        vlayout.addLayout(hlayout)

        groupbox.setLayout(vlayout)
        global_vlayout.addWidget(groupbox)

        # text processing rules
        # =====================
        groupbox = aqt.qt.QGroupBox('Text Processing Rules')
        vlayout = aqt.qt.QVBoxLayout()

        self.html_to_text_line_checkbox = aqt.qt.QCheckBox('Process HTML tags, convert into single line')
        vlayout.addWidget(self.html_to_text_line_checkbox)
        self.strip_brackets_checkbox = aqt.qt.QCheckBox('Remove text in brackets (), [], {}, <>')
        vlayout.addWidget(self.strip_brackets_checkbox)
        self.strip_cloze_checkbox = aqt.qt.QCheckBox('Remove Cloze brackets {{c1::text}}')
        vlayout.addWidget(self.strip_cloze_checkbox)
        self.ssml_convert_characters_checkbox = aqt.qt.QCheckBox('Convert SSML characters (like <, &&, etc)')
        vlayout.addWidget(self.ssml_convert_characters_checkbox)
        self.run_replace_rules_after_checkbox = aqt.qt.QCheckBox('Run text replacement rules last (uncheck to run first)')
        vlayout.addWidget(self.run_replace_rules_after_checkbox)
        self.ignore_case_checkbox = aqt.qt.QCheckBox('Ignore case (Regex rules only)')
        vlayout.addWidget(self.ignore_case_checkbox)

        groupbox.setLayout(vlayout)
        global_vlayout.addWidget(groupbox)

        # setup preview table
        # ===================

        groupbox = aqt.qt.QGroupBox('Text Replacement Rules')
        vlayout = aqt.qt.QVBoxLayout()        

        vlayout.addWidget(aqt.qt.QLabel('Add replacement rules and double click to edit pattern / replacements'))

        self.table_view = aqt.qt.QTableView()
        self.table_view.setModel(self.textReplacementTableModel)
        self.table_view.setSelectionMode(aqt.qt.QTableView.SelectionMode.SingleSelection)
        # self.table_view.setSelectionBehavior(aqt.qt.QTableView.SelectionBehavior.SelectRows)
        vlayout.addWidget(self.table_view)
        
        # setup buttons below table
        hlayout = aqt.qt.QHBoxLayout()
        self.add_replace_simple_button = aqt.qt.QPushButton('Add Simple Rule')
        hlayout.addWidget(self.add_replace_simple_button)
        self.add_replace_regex_button = aqt.qt.QPushButton('Add Regex Rule')
        hlayout.addWidget(self.add_replace_regex_button)
        self.remove_replace_button = aqt.qt.QPushButton('Remove Selected Rule')
        hlayout.addWidget(self.remove_replace_button)
        vlayout.addLayout(hlayout)

        groupbox.setLayout(vlayout)
        global_vlayout.addWidget(groupbox)        

        # wire events
        # ===========
        self.html_to_text_line_checkbox.stateChanged.connect(self.html_to_text_line_checkbox_change)
        self.strip_brackets_checkbox.stateChanged.connect(self.strip_brackets_change)
        self.strip_cloze_checkbox.stateChanged.connect(self.strip_cloze_change)
        self.ssml_convert_characters_checkbox.stateChanged.connect(self.ssml_convert_characters_checkbox_change)
        self.run_replace_rules_after_checkbox.stateChanged.connect(self.run_replace_rules_after_checkbox_change)
        self.ignore_case_checkbox.stateChanged.connect(self.ignore_case_checkbox_change)

        self.add_replace_simple_button.pressed.connect(lambda: self.textReplacementTableModel.add_replacement(constants.TextReplacementRuleType.Simple))
        self.add_replace_regex_button.pressed.connect(lambda: self.textReplacementTableModel.add_replacement(constants.TextReplacementRuleType.Regex))
        self.remove_replace_button.pressed.connect(self.delete_text_replacement)
        self.typing_timer = self.hypertts.anki_utils.wire_typing_timer(self.sample_text_input, self.update_transformed_text)

        self.set_text_processing_rules_widget_state()

        self.model_change()

        self.scroll_area.setWidget(self.layout_widget)
        return self.scroll_area

    def set_text_processing_rules_widget_state(self):
        self.html_to_text_line_checkbox.setChecked(self.model.html_to_text_line)
        self.strip_brackets_checkbox.setChecked(self.model.strip_brackets)
        self.strip_cloze_checkbox.setChecked(self.model.strip_cloze)
        self.ssml_convert_characters_checkbox.setChecked(self.model.ssml_convert_characters)
        self.run_replace_rules_after_checkbox.setChecked(self.model.run_replace_rules_after)

    def html_to_text_line_checkbox_change(self, value):
        enabled = value == 2
        self.model.html_to_text_line = enabled
        logger.info(f'self.model.html_to_text_line: {self.model.html_to_text_line}')
        self.model_change()

    def strip_brackets_change(self, value):
        enabled = value == 2
        self.model.strip_brackets = enabled
        self.model_change()        

    def strip_cloze_change(self, value):
        enabled = value == 2
        self.model.strip_cloze = enabled
        self.model_change()

    def ssml_convert_characters_checkbox_change(self, value):
        enabled = value == 2
        self.model.ssml_convert_characters = enabled
        self.model_change()

    def run_replace_rules_after_checkbox_change(self, value):
        enabled = value == 2
        self.model.run_replace_rules_after = enabled
        self.model_change()

    def ignore_case_checkbox_change(self, value):
        enabled = value == 2
        self.model.ignore_case = enabled
        self.model_change()        

    def model_change(self):
        self.update_transformed_text()
        self.model_change_callback(self.model)

    def get_text_processing_settings(self):
        replacement_list = self.textReplacementTableModel.replacements
        replacement_dict_list = [x.to_dict() for x in replacement_list]
        return {'replacements': replacement_dict_list}

    def update_transformed_text(self):
        # get the sample text
        sample_text = self.sample_text_input.text()
        if len(sample_text) == 0:
            label_text = BLANK_TEXT
        else:
            try:
                # get the text replacements
                processed_text = text_utils.process_text(sample_text, self.model)
                label_text = f'<b>{html.escape(processed_text)}</b>'
            except Exception as e:
                label_text = f'<b>error: {str(e)}</b>'

        # self.sample_text_transformed_label.setText(label_text)
        self.hypertts.anki_utils.run_on_main(lambda: self.sample_text_transformed_label.setText(label_text))


    def delete_text_replacement(self):
        rows_indices = self.table_view.selectionModel().selectedIndexes()
        if len(rows_indices) == 1:
            self.textReplacementTableModel.delete_rows(rows_indices[0])
