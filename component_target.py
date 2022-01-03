import PyQt5

class BatchTarget():
    def __init__(self, hypertts, note_id_list):
        self.hypertts = hypertts
        self.note_id_list = note_id_list
        self.field_list = self.hypertts.get_all_fields_from_notes(self.note_id_list)

        self.batch_target_model = None

    def draw(self, layout):
        self.batch_target_layout = PyQt5.QtWidgets.QVBoxLayout()
        layout.addLayout(self.batch_target_layout)
        
        # target field
        self.target_field_combobox = PyQt5.QtWidgets.QComboBox()
        self.target_field_combobox.addItems(self.field_list)
        self.batch_target_layout.addWidget(self.target_field_combobox)

        # text and sound tag
        self.text_sound_group = PyQt5.QtWidgets.QButtonGroup()
        self.radio_button_sound_only = PyQt5.QtWidgets.QRadioButton('Sound Tag only')
        self.radio_button_text_sound = PyQt5.QtWidgets.QRadioButton('Text and Sound Tag')
        self.text_sound_group.addButton(self.radio_button_sound_only)
        self.text_sound_group.addButton(self.radio_button_text_sound)
        self.radio_button_sound_only.setChecked(True)
        self.batch_target_layout.addWidget(self.radio_button_sound_only)
        self.batch_target_layout.addWidget(self.radio_button_text_sound)

        # remove sound tag
        self.remove_sound_group = PyQt5.QtWidgets.QButtonGroup()
        self.radio_button_remove_sound = PyQt5.QtWidgets.QRadioButton('Remove other sound tags')
        self.radio_button_keep_sound = PyQt5.QtWidgets.QRadioButton('Keep other sound tags')
        self.remove_sound_group.addButton(self.radio_button_remove_sound)
        self.remove_sound_group.addButton(self.radio_button_keep_sound)
        self.radio_button_remove_sound.setChecked(True)
        self.batch_target_layout.addWidget(self.radio_button_remove_sound)
        self.batch_target_layout.addWidget(self.radio_button_keep_sound)



    