import PyQt5
import logging
import config_models

import constants

class SourceTextPreviewTableModel(PyQt5.QtCore.QAbstractTableModel):
    def __init__(self):
        PyQt5.QtCore.QAbstractTableModel.__init__(self, None)
        self.source_records = []
        self.note_id_header = 'Note Id'
        self.source_text_header = 'Source Text'

    def flags(self, index):
        return PyQt5.QtCore.Qt.ItemIsSelectable | PyQt5.QtCore.Qt.ItemIsEnabled

    def setSourceRecords(self, source_records):
        logging.debug('SourceTextPreviewTableModel.setSourceRecords')
        self.source_records = source_records
        start_index = self.createIndex(0, 0)
        end_index = self.createIndex(len(self.source_records)-1, 1)
        self.dataChanged.emit(start_index, end_index, [PyQt5.QtCore.Qt.DisplayRole])
        self.layoutChanged.emit()

    def rowCount(self, parent):
        # logging.debug('SourceTextPreviewTableModel.rowCount')
        return len(self.source_records)

    def columnCount(self, parent):
        # logging.debug('SourceTextPreviewTableModel.columnCount')
        return 2

    def data(self, index, role):
        # logging.debug('SourceTextPreviewTableModel.data')
        if not index.isValid():
            return PyQt5.QtCore.QVariant()
        elif role != PyQt5.QtCore.Qt.DisplayRole:
           return PyQt5.QtCore.QVariant()
        if index.column() == 0:
            # note_id
            return PyQt5.QtCore.QVariant(self.source_records[index.row()][0])
        else:
            # source text field
            return PyQt5.QtCore.QVariant(self.source_records[index.row()][1])

    def headerData(self, col, orientation, role):
        # logging.debug('SourceTextPreviewTableModel.headerData')
        if orientation == PyQt5.QtCore.Qt.Horizontal and role == PyQt5.QtCore.Qt.DisplayRole:
            if col == 0:
                return PyQt5.QtCore.QVariant(self.note_id_header)
            else:
                return PyQt5.QtCore.QVariant(self.source_text_header)
        return PyQt5.QtCore.QVariant()

class BatchSource():
    def __init__(self, hypertts, note_id_list):
        self.hypertts = hypertts
        self.note_id_list = note_id_list
        self.field_list = self.hypertts.get_all_fields_from_notes(self.note_id_list)

        self.source_text_preview_table_model = SourceTextPreviewTableModel()

        self.batch_source_model = None

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

        self.table_view = PyQt5.QtWidgets.QTableView()
        self.table_view.setModel(self.source_text_preview_table_model)
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, PyQt5.QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, PyQt5.QtWidgets.QHeaderView.Stretch)
        self.batch_source_layout.addWidget(self.table_view)

        # wire events
        self.batch_mode_combobox.currentIndexChanged.connect(self.batch_mode_change)
        self.source_field_combobox.currentIndexChanged.connect(self.source_field_change)

    def batch_mode_change(self, current_index):
        selected_batch_mode = constants.BatchMode[self.batch_mode_combobox.currentText()]

        self.source_field_combobox.setVisible(False)

        if selected_batch_mode == constants.BatchMode.simple:
            self.source_field_combobox.setVisible(True)
        elif selected_batch_mode == constants.BatchMode.template:
            pass
        elif selected_batch_mode == constants.BatchMode.advanced_template:
            pass

    def source_field_change(self, current_index):
        field_name = self.field_list[current_index]
        self.batch_source_model = config_models.BatchSourceSimple(field_name)
        self.update_source_text_preview()

    def update_source_text_preview(self):
        field_values = self.hypertts.get_source_text_array(self.note_id_list, self.batch_source_model)
        self.source_text_preview_table_model.setSourceRecords(field_values)        
