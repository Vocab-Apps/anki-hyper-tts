import sys
import aqt.qt

from . import component_target
from . import config_models
from . import constants
from . import logging_utils
logger = logging_utils.get_child_logger(__name__)


class BatchTargetEasy(component_target.BatchTarget):
    def __init__(self, hypertts, field_list, model_change_callback):
        logger.debug('BatchTargetEasy.__init__')
        super().__init__(hypertts, field_list, model_change_callback)

        # initialize widgets
        # same field
        self.same_field_group = aqt.qt.QButtonGroup()
        self.radio_button_same_field = aqt.qt.QRadioButton(f'Into same field')
        self.radio_button_different_field = aqt.qt.QRadioButton('Into different field (choose which)')
        self.same_field_group.addButton(self.radio_button_same_field)
        self.same_field_group.addButton(self.radio_button_different_field)
        # insert location
        self.insert_location_group = aqt.qt.QButtonGroup()
        self.radio_button_after = aqt.qt.QRadioButton('At the end')
        self.radio_button_cursor = aqt.qt.QRadioButton('After cursor (not supported)')
        self.insert_location_group.addButton(self.radio_button_after)
        self.insert_location_group.addButton(self.radio_button_cursor)        

    def draw(self):
        self.layout_widget = aqt.qt.QWidget()
        self.batch_target_layout = aqt.qt.QVBoxLayout(self.layout_widget)

        # Same field option
        target_field_container = aqt.qt.QWidget()
        vlayout = aqt.qt.QVBoxLayout(target_field_container)
        vlayout.addWidget(aqt.qt.QLabel('<i>Which field to insert the audio into?</i>'))
        vlayout.addWidget(self.radio_button_same_field)
        vlayout.addWidget(self.radio_button_different_field)

        # Target field combobox (only shown when different field selected)
        self.target_field_widget = aqt.qt.QWidget()
        target_field_layout = aqt.qt.QVBoxLayout(self.target_field_widget)
        target_field_layout.addWidget(aqt.qt.QLabel(constants.GUI_TEXT_TARGET_FIELD))
        self.target_field_combobox.addItems(self.field_list)
        target_field_layout.addWidget(self.target_field_combobox)
        vlayout.addWidget(self.target_field_widget)
        self.batch_target_layout.addWidget(target_field_container)

        # Insert location options (only shown when same field selected)
        self.insert_location_widget = aqt.qt.QWidget()
        insert_location_layout = aqt.qt.QVBoxLayout(self.insert_location_widget)
        insert_location_layout.addWidget(aqt.qt.QLabel('<i>Where inside the field to insert the audio?</i>'))
        insert_location_layout.addWidget(self.radio_button_after)
        insert_location_layout.addWidget(self.radio_button_cursor)
        self.batch_target_layout.addWidget(self.insert_location_widget)

        # Sound handling options (only shown when different field selected)
        self.sound_options_widget = aqt.qt.QWidget()
        sound_options_layout = aqt.qt.QVBoxLayout(self.sound_options_widget)

        # Text and sound tag
        text_sound_container = aqt.qt.QWidget()
        vlayout = aqt.qt.QVBoxLayout(text_sound_container)
        label = aqt.qt.QLabel(constants.GUI_TEXT_TARGET_TEXT_AND_SOUND)
        label.setWordWrap(True)
        vlayout.addWidget(label)
        vlayout.addWidget(self.radio_button_sound_only)
        vlayout.addWidget(self.radio_button_text_sound)
        sound_options_layout.addWidget(text_sound_container)

        # Remove sound tag
        sound_tag_container = aqt.qt.QWidget()
        vlayout = aqt.qt.QVBoxLayout(sound_tag_container)
        label = aqt.qt.QLabel(constants.GUI_TEXT_TARGET_REMOVE_SOUND_TAG)
        label.setWordWrap(True)
        vlayout.addWidget(label)
        vlayout.addWidget(self.radio_button_remove_sound)
        vlayout.addWidget(self.radio_button_keep_sound)
        sound_options_layout.addWidget(sound_tag_container)

        self.batch_target_layout.addWidget(self.sound_options_widget)
        self.batch_target_layout.addStretch()

        # Set initial state
        self.radio_button_same_field.setChecked(True)
        self.radio_button_after.setChecked(True)
        self.radio_button_text_sound.setChecked(True)
        self.radio_button_remove_sound.setChecked(True)        

        # Connect events
        self.wire_events()

        # Initial update
        self.update_field()
        self.update_same_field()
        self.update_text_sound()
        self.update_remove_sound() 

        return self.layout_widget

    def wire_events(self):
        self.wire_events_base()
        # same field
        self.radio_button_same_field.toggled.connect(self.update_same_field)
        self.radio_button_different_field.toggled.connect(self.update_same_field)
        # insert location
        self.radio_button_after.toggled.connect(self.update_insert_location)
        self.radio_button_cursor.toggled.connect(self.update_insert_location)

    def update_same_field(self):
        same_field = self.radio_button_same_field.isChecked()
        self.batch_target_model.same_field = same_field

        if same_field:
            # we are going to the same field, it will contain text and sound
            self.radio_button_text_sound.setChecked(True)
            # remove other tags by default
            self.radio_button_remove_sound.setChecked(True)
        else:
            # we are going to a different field, it will only contain sound
            self.radio_button_sound_only.setChecked(True)
            # remove other tags by default
            self.radio_button_remove_sound.setChecked(True)
        
        # Show/hide widgets based on same_field setting
        self.target_field_widget.setVisible(not same_field)
        self.sound_options_widget.setVisible(not same_field)
        self.insert_location_widget.setVisible(same_field)
        
        self.notify_model_update()

    def update_insert_location(self):
        if self.radio_button_after.isChecked():
            self.batch_target_model.insert_location = config_models.InsertLocation.AFTER
        else:
            self.batch_target_model.insert_location = config_models.InsertLocation.CURSOR_LOCATION
        self.notify_model_update()

    def load_model(self, model):
        logger.debug('load_model')
        self.batch_target_model = model

        # Set same field radio buttons
        self.radio_button_same_field.setChecked(model.same_field)
        self.radio_button_different_field.setChecked(not model.same_field)
        # Update visibility
        self.update_same_field()        

        # Set insert location radio buttons
        self.radio_button_after.setChecked(model.insert_location == config_models.InsertLocation.AFTER)
        self.radio_button_cursor.setChecked(model.insert_location == config_models.InsertLocation.CURSOR_LOCATION)

        # Set target field
        if model.target_field in self.field_list:
            self.target_field_combobox.setCurrentText(model.target_field)

        # Set sound handling options
        self.radio_button_text_sound.setChecked(model.text_and_sound_tag)
        self.radio_button_sound_only.setChecked(not model.text_and_sound_tag)
        self.radio_button_remove_sound.setChecked(model.remove_sound_tag)
        self.radio_button_keep_sound.setChecked(not model.remove_sound_tag)

