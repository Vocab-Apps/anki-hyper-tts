import logging
import PyQt5

import batch_status
import component_common


class BatchPreviewTableModel(PyQt5.QtCore.QAbstractTableModel):
    def __init__(self, batch_status):
        PyQt5.QtCore.QAbstractTableModel.__init__(self, None)
        self.batch_status = batch_status
        self.note_id_header = 'Note Id'
        self.source_text_header = 'Source Text'
        self.processed_text_header = 'Processed Text'
        self.status_header = 'Status'

    def flags(self, index):
        return PyQt5.QtCore.Qt.ItemIsSelectable | PyQt5.QtCore.Qt.ItemIsEnabled

    def rowCount(self, parent):
        # logging.debug('SourceTextPreviewTableModel.rowCount')
        return len(self.batch_status.note_id_list)

    def columnCount(self, parent):
        # logging.debug('SourceTextPreviewTableModel.columnCount')
        return 4
    
    def notifyChange(self, row):
        start_index = self.createIndex(row, 0)
        end_index = self.createIndex(row, 2)
        self.dataChanged.emit(start_index, end_index, [PyQt5.QtCore.Qt.DisplayRole])

    def data(self, index, role):
        if role != PyQt5.QtCore.Qt.DisplayRole:
            return None
        # logging.debug('SourceTextPreviewTableModel.data')
        if not index.isValid():
            return PyQt5.QtCore.QVariant()
        data = None
        note_status = self.batch_status[index.row()]
        if index.column() == 0:
            data = note_status.note_id
        elif index.column() == 1:
            data = note_status.source_text
        elif index.column() == 2:
            data = note_status.processed_text            
        elif index.column() == 2:
            if note_status.status != None:
                data = note_status.status.name
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
                return PyQt5.QtCore.QVariant(self.processed_text_header)
            elif col == 3:
                return PyQt5.QtCore.QVariant(self.status_header)
        return PyQt5.QtCore.QVariant()

class BatchPreview(component_common.ComponentBase):
    def __init__(self, hypertts, note_id_list, sample_selection_fn):
        self.hypertts = hypertts
        self.note_id_list = note_id_list
        self.sample_selection_fn = sample_selection_fn

        self.batch_status = batch_status.BatchStatus(hypertts.anki_utils, note_id_list, self.change_listener)
        self.batch_preview_table_model = BatchPreviewTableModel(self.batch_status)
    
    def load_model(self, model):
        self.batch_model = model
        self.hypertts.populate_batch_status_processed_text(self.note_id_list, self.batch_model.source, self.batch_status)

    def draw(self):
        # populate processed text

        self.batch_preview_layout = PyQt5.QtWidgets.QVBoxLayout()
        self.table_view = PyQt5.QtWidgets.QTableView()
        self.table_view.setModel(self.batch_preview_table_model)
        self.table_view.setSelectionMode(PyQt5.QtWidgets.QTableView.SingleSelection)
        self.table_view.setSelectionBehavior(PyQt5.QtWidgets.QTableView.SelectRows)
        self.table_view.selectionModel().selectionChanged.connect(self.selection_changed)
        self.batch_preview_layout.addWidget(self.table_view)

        self.preview_audio_button = PyQt5.QtWidgets.QPushButton('Preview Audio')
        self.batch_preview_layout.addWidget(self.preview_audio_button)

        self.load_audio_button = PyQt5.QtWidgets.QPushButton('Load Audio')
        self.batch_preview_layout.addWidget(self.load_audio_button)

        # wire events
        self.preview_audio_button.pressed.connect(self.preview_audio_button_pressed)
        self.load_audio_button.pressed.connect(self.load_audio_button_pressed)

        return self.batch_preview_layout

    def selection_changed(self):
        logging.info('selection_changed')
        text = self.get_selected_processed_text()
        if text != None:
            self.sample_selection_fn(text)

    def preview_audio_button_pressed(self):
        self.hypertts.anki_utils.run_in_background(self.play_preview_task, self.play_preview_task_done)

    def get_selected_processed_text(self):
        row_indices = self.table_view.selectionModel().selectedIndexes()
        if len(row_indices) >= 1:
            selected_row = row_indices[0].row()
            processed_text = self.batch_status[selected_row].processed_text
            return processed_text
        return None

    def play_preview_task(self):
        row_indices = self.table_view.selectionModel().selectedIndexes()
        if len(row_indices) >= 1:
            selected_row = row_indices[0].row()
            processed_text = self.batch_status[selected_row].processed_text
            self.hypertts.play_sound_batch_preview(processed_text, self.batch_model.voice_selection)

    def play_preview_task_done(self, result):
        pass

    def load_audio_button_pressed(self):
        self.hypertts.anki_utils.run_in_background(self.load_audio_task, self.load_audio_task_done)

    def load_audio_task(self):
        logging.info('load_audio_task')
        self.hypertts.process_batch_audio(self.note_id_list, self.batch_model, self.batch_status)

    def load_audio_task_done(self, result):
        logging.info('load_audio_task_done')

    def change_listener(self, note_id, row):
        # logging.info(f'change_listener row {row}')
        self.batch_preview_table_model.notifyChange(row)