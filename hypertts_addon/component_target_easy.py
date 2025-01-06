import sys
import aqt.qt

from . import component_target
from . import config_models
from . import constants
from . import logging_utils
logger = logging_utils.get_child_logger(__name__)


class BatchTargetEasy(component_target.BatchTarget):
    def __init__(self, hypertts, field_list, model_change_callback):
        super().__init__(hypertts, field_list, model_change_callback)
        self.batch_target_model = config_models.BatchTarget(None, False, True, config_models.InsertLocation.AFTER, False)

    def draw(self):
        self.scroll_area = aqt.qt.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.layout_widget = aqt.qt.QWidget()
        self.batch_target_layout = aqt.qt.QVBoxLayout(self.layout_widget)

        # Same field option
        groupbox = aqt.qt.QGroupBox('Target Field')
        vlayout = aqt.qt.QVBoxLayout()
        self.same_field_group = aqt.qt.QButtonGroup()
        self.radio_button_same_field = aqt.qt.QRadioButton('Use same field as source')
        self.radio_button_different_field = aqt.qt.QRadioButton('Use different field')
        self.same_field_group.addButton(self.radio_button_same_field)
        self.same_field_group.addButton(self.radio_button_different_field)
        vlayout.addWidget(self.radio_button_same_field)
        vlayout.addWidget(self.radio_button_different_field)

        # Target field combobox (only shown when different field selected)
        self.target_field_widget = aqt.qt.QWidget()
        target_field_layout = aqt.qt.QVBoxLayout(self.target_field_widget)
        target_field_layout.addWidget(aqt.qt.QLabel(constants.GUI_TEXT_TARGET_FIELD))
        self.target_field_combobox = aqt.qt.QComboBox()
        self.target_field_combobox.addItems(self.field_list)
        target_field_layout.addWidget(self.target_field_combobox)
        vlayout.addWidget(self.target_field_widget)
        groupbox.setLayout(vlayout)
        self.batch_target_layout.addWidget(groupbox)

        # Insert location options (only shown when same field selected)
        self.insert_location_widget = aqt.qt.QWidget()
        groupbox = aqt.qt.QGroupBox('Insert Location')
        vlayout = aqt.qt.QVBoxLayout()
        self.insert_location_group = aqt.qt.QButtonGroup()
        self.radio_button_after = aqt.qt.QRadioButton('After existing content')
        self.radio_button_cursor = aqt.qt.QRadioButton('At cursor location')
        self.insert_location_group.addButton(self.radio_button_after)
        self.insert_location_group.addButton(self.radio_button_cursor)
        vlayout.addWidget(self.radio_button_after)
        vlayout.addWidget(self.radio_button_cursor)
        groupbox.setLayout(vlayout)
        self.insert_location_widget.setLayout(aqt.qt.QVBoxLayout())
        self.insert_location_widget.layout().addWidget(groupbox)
        self.batch_target_layout.addWidget(self.insert_location_widget)

        # Sound handling options (only shown when different field selected)
        self.sound_options_widget = aqt.qt.QWidget()
        sound_options_layout = aqt.qt.QVBoxLayout(self.sound_options_widget)

        # Text and sound tag
        groupbox = aqt.qt.QGroupBox('Text and Sound Tag Handling')
        vlayout = aqt.qt.QVBoxLayout()
        label = aqt.qt.QLabel(constants.GUI_TEXT_TARGET_TEXT_AND_SOUND)
        label.setWordWrap(True)
        vlayout.addWidget(label)
        self.text_sound_group = aqt.qt.QButtonGroup()
        self.radio_button_sound_only = aqt.qt.QRadioButton('Sound Tag only')
        self.radio_button_text_sound = aqt.qt.QRadioButton('Text and Sound Tag')
        self.text_sound_group.addButton(self.radio_button_sound_only)
        self.text_sound_group.addButton(self.radio_button_text_sound)
        vlayout.addWidget(self.radio_button_sound_only)
        vlayout.addWidget(self.radio_button_text_sound)
        groupbox.setLayout(vlayout)
        sound_options_layout.addWidget(groupbox)

        # Remove sound tag
        groupbox = aqt.qt.QGroupBox('Existing Sound Tag Handling')
        vlayout = aqt.qt.QVBoxLayout()
        label = aqt.qt.QLabel(constants.GUI_TEXT_TARGET_REMOVE_SOUND_TAG)
        label.setWordWrap(True)
        vlayout.addWidget(label)
        self.remove_sound_group = aqt.qt.QButtonGroup()
        self.radio_button_remove_sound = aqt.qt.QRadioButton('Remove other sound tags')
        self.radio_button_keep_sound = aqt.qt.QRadioButton('Keep other sound tags (append)')
        self.remove_sound_group.addButton(self.radio_button_remove_sound)
        self.remove_sound_group.addButton(self.radio_button_keep_sound)
        vlayout.addWidget(self.radio_button_remove_sound)
        vlayout.addWidget(self.radio_button_keep_sound)
        groupbox.setLayout(vlayout)
        sound_options_layout.addWidget(groupbox)

        self.batch_target_layout.addWidget(self.sound_options_widget)
        self.batch_target_layout.addStretch()

        # Set initial state
        self.radio_button_different_field.setChecked(True)
        self.radio_button_sound_only.setChecked(True)
        self.radio_button_remove_sound.setChecked(True)
        self.radio_button_after.setChecked(True)

        # Connect events
        self.radio_button_same_field.toggled.connect(self.update_same_field)
        self.radio_button_different_field.toggled.connect(self.update_same_field)
        self.target_field_combobox.currentIndexChanged.connect(self.update_field)
        self.radio_button_sound_only.toggled.connect(self.update_text_sound)
        self.radio_button_text_sound.toggled.connect(self.update_text_sound)
        self.radio_button_remove_sound.toggled.connect(self.update_remove_sound)
        self.radio_button_keep_sound.toggled.connect(self.update_remove_sound)
        self.radio_button_after.toggled.connect(self.update_insert_location)
        self.radio_button_cursor.toggled.connect(self.update_insert_location)

        # Initial update
        self.update_same_field()
        self.update_field()

        self.scroll_area.setWidget(self.layout_widget)
        return self.scroll_area

    def update_same_field(self):
        same_field = self.radio_button_same_field.isChecked()
        self.batch_target_model.same_field = same_field
        
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
        self.batch_target_model = model

        # Set same field radio buttons
        self.radio_button_same_field.setChecked(model.same_field)
        self.radio_button_different_field.setChecked(not model.same_field)

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

        # Update visibility
        self.update_same_field()
