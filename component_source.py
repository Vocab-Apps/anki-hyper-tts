import PyQt5
import logging
import config_models
import component_common
import batch_status

import constants

class SourceTextPreviewTableModel(PyQt5.QtCore.QAbstractTableModel):
    def __init__(self, batch_status):
        PyQt5.QtCore.QAbstractTableModel.__init__(self, None)
        self.batch_status = batch_status
        self.note_id_header = 'Note Id'
        self.source_text_header = 'Source Text'
        self.error_header = 'Error'

    def flags(self, index):
        return PyQt5.QtCore.Qt.ItemIsSelectable | PyQt5.QtCore.Qt.ItemIsEnabled

    def setSourceRecords(self, source_records):
        logging.debug('SourceTextPreviewTableModel.setSourceRecords')
        self.source_records = source_records
        start_index = self.createIndex(0, 0)
        end_index = self.createIndex(len(self.source_records)-1, 1)
        self.dataChanged.emit(start_index, end_index, [PyQt5.QtCore.Qt.DisplayRole])
        self.layoutChanged.emit()

    def notifyChange(self, row):
        start_index = self.createIndex(row, 0)
        end_index = self.createIndex(row, 2)
        self.dataChanged.emit(start_index, end_index, [PyQt5.QtCore.Qt.DisplayRole])

    def rowCount(self, parent):
        return len(self.batch_status.note_id_list)

    def columnCount(self, parent):
        return 3

    def data(self, index, role):
        # logging.debug('SourceTextPreviewTableModel.data')
        if not index.isValid():
            return PyQt5.QtCore.QVariant()
        elif role != PyQt5.QtCore.Qt.DisplayRole:
           return PyQt5.QtCore.QVariant()
        note_status = self.batch_status[index.row()]
        if index.column() == 0:
            data = note_status.note_id
        elif index.column() == 1:
            data = note_status.source_text
        elif index.column() == 2:
            if note_status.error == None:
                data = None
            else:
                data = str(note_status.error)
        if data != None:
            return PyQt5.QtCore.QVariant(data)
        return PyQt5.QtCore.QVariant()

    def headerData(self, col, orientation, role):
        # logging.debug('SourceTextPreviewTableModel.headerData')
        if orientation == PyQt5.QtCore.Qt.Horizontal and role == PyQt5.QtCore.Qt.DisplayRole:
            if col == 0:
                return PyQt5.QtCore.QVariant(self.note_id_header)
            elif col == 1:
                return PyQt5.QtCore.QVariant(self.source_text_header)
            elif col == 2:
                return PyQt5.QtCore.QVariant(self.error_header)
        return PyQt5.QtCore.QVariant()

class BatchSource(component_common.ConfigComponentBase):
    def __init__(self, hypertts, note_id_list):
        self.hypertts = hypertts
        self.note_id_list = note_id_list
        self.field_list = self.hypertts.get_all_fields_from_notes(self.note_id_list)

        self.batch_status = batch_status.BatchStatus(hypertts.anki_utils, note_id_list, self.change_listener)
        self.source_text_preview_table_model = SourceTextPreviewTableModel(self.batch_status)

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

        self.update_source_text_preview()

    def draw(self, layout):
        self.batch_source_layout = PyQt5.QtWidgets.QVBoxLayout()
        layout.addLayout(self.batch_source_layout)

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

        # preview table
        self.table_view = PyQt5.QtWidgets.QTableView()
        self.table_view.setModel(self.source_text_preview_table_model)
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, PyQt5.QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, PyQt5.QtWidgets.QHeaderView.Stretch)
        self.batch_source_layout.addWidget(self.table_view)

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
        self.update_source_text_preview()

    def simple_template_change(self, simple_template_text):
        simple_template_text = self.simple_template_input.text()
        self.batch_source_model = config_models.BatchSourceTemplate(constants.BatchMode.template, simple_template_text, constants.TemplateFormatVersion.v1)
        self.update_source_text_preview()

    def advanced_template_change(self):
        template_text = self.advanced_template_input.toPlainText()
        self.batch_source_model = config_models.BatchSourceTemplate(constants.BatchMode.advanced_template, template_text, constants.TemplateFormatVersion.v1)
        self.update_source_text_preview()        

    def change_listener(self, note_id, row):
        # logging.info(f'change_listener row {row}')
        self.source_text_preview_table_model.notifyChange(row)

    def update_source_text_preview(self):
        self.hypertts.populate_batch_status_source_text(self.note_id_list, self.batch_source_model, self.batch_status)
