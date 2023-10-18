import sys
import aqt.qt

from typing import List, Optional

component_common = __import__('component_common', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
component_batch = __import__('component_batch', globals(), locals(), [], sys._addon_import_level_base)


class ComponentChoosePreset(component_common.ComponentBase):
    def __init__(self, hypertts, dialog):
        self.hypertts = hypertts
        self.dialog = dialog
        self.new_preset = True
        self.preset_id = None
        self.selected_ok = False

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
        if existing_presets_available:
            self.preset_id = self.preset_list[0].id

        # wire events
        self.new_preset_radio_button.toggled.connect(self.new_preset_radio_button_checked)
        self.existing_preset_radio_button.toggled.connect(self.existing_preset_radio_button_checked)
        self.preset_combo_box.currentIndexChanged.connect(self.preset_combo_box_changed)

        # add buttons at the bottom
        hlayout = aqt.qt.QHBoxLayout()
        hlayout.addStretch()
        self.ok_button = aqt.qt.QPushButton('Ok')
        self.cancel_button = aqt.qt.QPushButton('Cancel')
        hlayout.addWidget(self.ok_button)
        hlayout.addWidget(self.cancel_button)

        self.ok_button.pressed.connect(self.ok_button_pressed)
        self.cancel_button.pressed.connect(self.cancel_button_pressed)

        self.vlayout.addStretch()
        self.vlayout.addLayout(hlayout)

        layout.addLayout(self.vlayout)

        self.update_controls_state()

    def update_controls_state(self):
        self.new_preset = self.new_preset_radio_button.isChecked()
        self.preset_combo_box.setEnabled(not self.new_preset)

    def new_preset_radio_button_checked(self):
        self.update_controls_state()

    def existing_preset_radio_button_checked(self):
        self.update_controls_state()

    def preset_combo_box_changed(self, index):
        self.preset_id = self.preset_combo_box.itemData(index).id
        self.update_controls_state()

    def ok_button_pressed(self):
        self.selected_ok = True
        self.dialog.close()

    def cancel_button_pressed(self):
        self.selected_ok = False
        self.dialog.close()

# factory methods

class ChoosePresetDialog(aqt.qt.QDialog):
    def __init__(self, hypertts):
        super(aqt.qt.QDialog, self).__init__()
        self.setupUi()
        self.choose_preset = ComponentChoosePreset(hypertts, self)
        self.choose_preset.draw(self.main_layout)
    
    def setupUi(self):
        self.setWindowTitle(constants.GUI_CHOOSE_PRESET_DIALOG_TITLE)        
        self.main_layout = aqt.qt.QVBoxLayout(self)

    def close(self):
        self.closed = True
        self.accept()

def get_preset_id(hypertts, editor_context: config_models.EditorContext) -> Optional[str]:
    dialog = ChoosePresetDialog(hypertts)
    hypertts.anki_utils.wait_for_dialog_input(dialog, constants.DIALOG_ID_CHOOSE_PRESET)
    if dialog.choose_preset.selected_ok:
        if dialog.choose_preset.new_preset:
            return component_batch.create_dialog_editor_new_preset(hypertts, editor_context)
        else:
            return dialog.choose_preset.preset_id
    else:
        return None