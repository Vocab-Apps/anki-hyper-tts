import PyQt5

import constants

class BatchSource():
    def __init__(self, hypertts, note_id_list):
        self.hypertts = hypertts
        self.note_id_list = note_id_list
        self.field_list = self.hypertts.anki_utils.get_all_fields_from_notes(self.note_id_list)

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

        # wire events
        self.batch_mode_combobox.currentIndexChanged.connect(self.batch_mode_change)

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
        pass
