from asyncio.proactor_events import constants
import sys
import PyQt5
import logging

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)


class BatchTarget(component_common.ConfigComponentBase):
    def __init__(self, hypertts, field_list, model_change_callback):
        self.hypertts = hypertts
        self.field_list = field_list
        self.model_change_callback = model_change_callback

        self.batch_target_model = config_models.BatchTarget(None, False, True)

    def get_model(self):
        return self.batch_target_model

    def load_model(self, model):
        logging.info('load_model')
        self.batch_target_model = model

        self.target_field_combobox.setCurrentText(self.batch_target_model.target_field)

        self.radio_button_text_sound.setChecked(self.batch_target_model.text_and_sound_tag)
        self.radio_button_sound_only.setChecked(not self.batch_target_model.text_and_sound_tag)
        self.radio_button_remove_sound.setChecked(self.batch_target_model.remove_sound_tag)
        self.radio_button_keep_sound.setChecked(not self.batch_target_model.remove_sound_tag)


    def draw(self):
        self.batch_target_layout = PyQt5.QtWidgets.QVBoxLayout()
        
        # target field
        # ============
        groupbox = PyQt5.QtWidgets.QGroupBox('Target Field')
        vlayout = PyQt5.QtWidgets.QVBoxLayout()
        vlayout.addWidget(PyQt5.QtWidgets.QLabel(constants.GUI_TEXT_TARGET_FIELD))
        self.target_field_combobox = PyQt5.QtWidgets.QComboBox()
        self.target_field_combobox.addItems(self.field_list)
        vlayout.addWidget(self.target_field_combobox)
        groupbox.setLayout(vlayout)
        self.batch_target_layout.addWidget(groupbox)

        # text and sound tag
        # ==================
        groupbox = PyQt5.QtWidgets.QGroupBox('Text and Sound Tag Handling')
        vlayout = PyQt5.QtWidgets.QVBoxLayout()
        label = PyQt5.QtWidgets.QLabel(constants.GUI_TEXT_TARGET_TEXT_AND_SOUND)
        label.setWordWrap(True)
        vlayout.addWidget(label)
        self.text_sound_group = PyQt5.QtWidgets.QButtonGroup()
        self.radio_button_sound_only = PyQt5.QtWidgets.QRadioButton('Sound Tag only')
        self.radio_button_text_sound = PyQt5.QtWidgets.QRadioButton('Text and Sound Tag')
        self.text_sound_group.addButton(self.radio_button_sound_only)
        self.text_sound_group.addButton(self.radio_button_text_sound)
        self.radio_button_sound_only.setChecked(True)
        vlayout.addWidget(self.radio_button_sound_only)
        vlayout.addWidget(self.radio_button_text_sound)
        groupbox.setLayout(vlayout)
        self.batch_target_layout.addWidget(groupbox)        

        # remove sound tag
        # ================
        groupbox = PyQt5.QtWidgets.QGroupBox('Existing Sound Tag Handling')
        vlayout = PyQt5.QtWidgets.QVBoxLayout()        
        label = PyQt5.QtWidgets.QLabel(constants.GUI_TEXT_TARGET_REMOVE_SOUND_TAG)
        label.setWordWrap(True)
        vlayout.addWidget(label)        
        self.remove_sound_group = PyQt5.QtWidgets.QButtonGroup()
        self.radio_button_remove_sound = PyQt5.QtWidgets.QRadioButton('Remove other sound tags')
        self.radio_button_keep_sound = PyQt5.QtWidgets.QRadioButton('Keep other sound tags (append)')
        self.remove_sound_group.addButton(self.radio_button_remove_sound)
        self.remove_sound_group.addButton(self.radio_button_keep_sound)
        self.radio_button_remove_sound.setChecked(True)
        vlayout.addWidget(self.radio_button_remove_sound)
        vlayout.addWidget(self.radio_button_keep_sound)
        groupbox.setLayout(vlayout)
        self.batch_target_layout.addWidget(groupbox)                

        self.batch_target_layout.addStretch()

        # connect events
        self.target_field_combobox.currentIndexChanged.connect(lambda x: self.update_field())
        self.radio_button_sound_only.toggled.connect(self.update_text_sound)
        self.radio_button_text_sound.toggled.connect(self.update_text_sound)
        self.radio_button_remove_sound.toggled.connect(self.update_remove_sound)
        self.radio_button_keep_sound.toggled.connect(self.update_remove_sound)

        # select default to trigger model update
        self.update_field()

        return self.batch_target_layout

    def update_text_sound(self):
        self.batch_target_model.text_and_sound_tag = self.radio_button_text_sound.isChecked()
        self.notify_model_update()

    def update_remove_sound(self):
        self.batch_target_model.remove_sound_tag = self.radio_button_remove_sound.isChecked()
        self.notify_model_update()

    def update_field(self):
        self.batch_target_model.target_field = self.field_list[self.target_field_combobox.currentIndex()]
        self.notify_model_update()

    def notify_model_update(self):
        self.model_change_callback(self.batch_target_model)