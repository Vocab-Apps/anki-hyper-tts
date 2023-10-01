import sys
import aqt.qt

from typing import List, Optional

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)


class ComponentChoosePreset(component_common.ComponentBase):
    def __init__(self, hypertts, dialog):
        self.hypertts = hypertts
        self.dialog = dialog
        self.new_preset = True
        self.preset_id = None

    def draw(self, layout):
        self.vlayout = aqt.qt.QVBoxLayout()

        self.existing_or_new = aqt.qt.QButtonGroup()
        self.new_preset_radio_button = aqt.qt.QRadioButton('New Preset')
        self.existing_preset_radio_button = aqt.qt.QRadioButton('Existing Preset')
        self.existing_or_new.addButton(self.new_preset_radio_button)
        self.existing_or_new.addButton(self.existing_preset_radio_button)
        self.new_preset_radio_button.setChecked(True)
        self.vlayout.addWidget(self.new_preset_radio_button)
        self.vlayout.addWidget(self.existing_preset_radio_button)

        self.preset_combo_box = aqt.qt.QComboBox()
        # get preset list
        self.preset_list: List[config_models.PresetInfo] = self.hypertts.get_preset_list()
        for preset_info in self.preset_list:
            self.preset_combo_box.addItem(preset_info.name, preset_info)
        self.vlayout.addWidget(self.preset_combo_box)
        
        # only enable "existing preset" if we have at least one preset
        existing_presets_available = len(self.preset_list) > 0
        self.existing_preset_radio_button.setEnabled(existing_presets_available)
        self.preset_combo_box.setEnabled(existing_presets_available)

        # wire events
        self.new_preset_radio_button.toggled.connect(self.new_preset_radio_button_checked)
        self.existing_preset_radio_button.toggled.connect(self.existing_preset_radio_button_checked)

        layout.addLayout(self.vlayout)

    def update_controls_state(self):
        self.new_preset = self.new_preset_radio_button.isChecked()
        self.preset_combo_box.setEnabled(not self.new_preset)

    def new_preset_radio_button_checked(self):
        self.update_controls_state()

    def existing_preset_radio_button_checked(self):
        self.update_controls_state()