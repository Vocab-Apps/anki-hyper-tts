from asyncio.proactor_events import constants
import sys
import aqt.qt

from . import component_common
from . import config_models
from . import constants
from . import logging_utils
logger = logging_utils.get_child_logger(__name__)


class BatchTarget(component_common.ConfigComponentBase):
    def __init__(self, hypertts, field_list, model_change_callback):
        self.hypertts = hypertts
        self.field_list = field_list
        self.model_change_callback = model_change_callback

        self.batch_target_model = config_models.BatchTarget()

        # initialize widgets
        self.target_field_combobox = aqt.qt.QComboBox()
        # text and sound
        self.text_sound_group = aqt.qt.QButtonGroup()
        self.radio_button_sound_only = aqt.qt.QRadioButton('Sound Tag only')
        self.radio_button_text_sound = aqt.qt.QRadioButton('Text and Sound Tag')
        self.text_sound_group.addButton(self.radio_button_sound_only)
        self.text_sound_group.addButton(self.radio_button_text_sound)
        # remove sound
        self.remove_sound_group = aqt.qt.QButtonGroup()
        self.radio_button_remove_sound = aqt.qt.QRadioButton('Remove other sound tags')
        self.radio_button_keep_sound = aqt.qt.QRadioButton('Keep other sound tags (append)')
        self.remove_sound_group.addButton(self.radio_button_remove_sound)
        self.remove_sound_group.addButton(self.radio_button_keep_sound)


    def get_model(self):
        return self.batch_target_model

    def load_model(self, model):
        logger.info('load_model')
        self.batch_target_model = model

        self.target_field_combobox.setCurrentText(self.batch_target_model.target_field)

        self.radio_button_text_sound.setChecked(self.batch_target_model.text_and_sound_tag)
        self.radio_button_sound_only.setChecked(not self.batch_target_model.text_and_sound_tag)
        self.radio_button_remove_sound.setChecked(self.batch_target_model.remove_sound_tag)
        self.radio_button_keep_sound.setChecked(not self.batch_target_model.remove_sound_tag)

        # ensure model at the higher level gets updated
        # this is important for example if the target field doesn't exist in the field list, we want to make
        # sure the model is updated to select another field
        self.update_field()


    def draw(self): # return scrollarea
        self.scroll_area = aqt.qt.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.layout_widget = aqt.qt.QWidget()

        self.batch_target_layout = aqt.qt.QVBoxLayout(self.layout_widget)
        
        # target field
        # ============
        groupbox = aqt.qt.QGroupBox('Target Field')
        vlayout = aqt.qt.QVBoxLayout()
        vlayout.addWidget(aqt.qt.QLabel(constants.GUI_TEXT_TARGET_FIELD))
        self.target_field_combobox.addItems(self.field_list)
        vlayout.addWidget(self.target_field_combobox)
        groupbox.setLayout(vlayout)
        self.batch_target_layout.addWidget(groupbox)


        # text and sound tag
        # ==================
        groupbox = aqt.qt.QGroupBox('Text and Sound Tag Handling')
        vlayout = aqt.qt.QVBoxLayout()
        label = aqt.qt.QLabel(constants.GUI_TEXT_TARGET_TEXT_AND_SOUND)
        label.setWordWrap(True)
        vlayout.addWidget(label)
        self.radio_button_sound_only.setChecked(True)
        vlayout.addWidget(self.radio_button_sound_only)
        vlayout.addWidget(self.radio_button_text_sound)
        groupbox.setLayout(vlayout)
        self.batch_target_layout.addWidget(groupbox)        

        # remove sound tag
        # ================
        groupbox = aqt.qt.QGroupBox('Existing Sound Tag Handling')
        vlayout = aqt.qt.QVBoxLayout()        
        label = aqt.qt.QLabel(constants.GUI_TEXT_TARGET_REMOVE_SOUND_TAG)
        label.setWordWrap(True)
        vlayout.addWidget(label)        
        self.radio_button_remove_sound.setChecked(True)
        vlayout.addWidget(self.radio_button_remove_sound)
        vlayout.addWidget(self.radio_button_keep_sound)
        groupbox.setLayout(vlayout)
        self.batch_target_layout.addWidget(groupbox)                

        self.batch_target_layout.addStretch()

        # connect events
        self.wire_events_base()

        # select default to trigger model update
        self.update_field()

        self.scroll_area.setWidget(self.layout_widget)
        return self.scroll_area

    def wire_events_base(self):
        logger.info('wire events base')
        self.target_field_combobox.currentIndexChanged.connect(lambda x: self.update_field())
        self.radio_button_sound_only.toggled.connect(self.update_text_sound)
        self.radio_button_text_sound.toggled.connect(self.update_text_sound)
        self.radio_button_remove_sound.toggled.connect(self.update_remove_sound)
        self.radio_button_keep_sound.toggled.connect(self.update_remove_sound)

    def update_text_sound(self):
        self.batch_target_model.text_and_sound_tag = self.radio_button_text_sound.isChecked()
        self.notify_model_update()

    def update_remove_sound(self):
        self.batch_target_model.remove_sound_tag = self.radio_button_remove_sound.isChecked()
        self.notify_model_update()

    def update_field(self):
        logger.info('update_field')
        self.batch_target_model.target_field = self.field_list[self.target_field_combobox.currentIndex()]
        self.notify_model_update()

    def notify_model_update(self):
        self.model_change_callback(self.batch_target_model)