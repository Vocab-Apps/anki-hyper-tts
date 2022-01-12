import logging
import PyQt5

import component_common


class BatchPreviewTableModel(PyQt5.QtCore.QAbstractTableModel):
    def __init__(self):
        PyQt5.QtCore.QAbstractTableModel.__init__(self, None)
        self.source_records = []
        self.note_id_header = 'Note Id'
        self.source_text_header = 'Text'
        self.status_header = 'Status'

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
        return 3

    def data(self, index, role):
        if role != PyQt5.QtCore.Qt.DisplayRole:
            return None
        # logging.debug('SourceTextPreviewTableModel.data')
        if not index.isValid():
            return PyQt5.QtCore.QVariant()
        if index.column() <= 2:
            data = self.source_records[index.row()][index.column()]
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
                return PyQt5.QtCore.QVariant(self.status_header)
        return PyQt5.QtCore.QVariant()

class BatchPreview(component_common.ComponentBase):
    def __init__(self, hypertts, batch_model, note_id_list):
        self.hypertts = hypertts
        self.batch_model = batch_model
        self.note_id_list = note_id_list

        self.batch_preview_table_model = BatchPreviewTableModel()
    
    def draw(self, layout):
        field_values = self.hypertts.get_source_text_array(self.note_id_list, self.batch_model.source)
        self.batch_preview_table_model.setSourceRecords(field_values)

        self.batch_preview_layout = PyQt5.QtWidgets.QVBoxLayout()
        self.table_view = PyQt5.QtWidgets.QTableView()
        self.table_view.setModel(self.batch_preview_table_model)
        self.batch_preview_layout.addWidget(self.table_view)

        layout.addLayout(self.batch_preview_layout)
