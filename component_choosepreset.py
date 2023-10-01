import sys
import aqt.qt

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)


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

        layout.addLayout(self.vlayout)