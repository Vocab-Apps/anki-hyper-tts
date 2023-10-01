import sys
import os
import logging
import aqt.qt

addon_dir = os.path.dirname(os.path.realpath(__file__))
external_dir = os.path.join(addon_dir, 'external')
sys.path.insert(0, external_dir)

import constants
import testing_utils
import gui_testing_utils
import component_choosepreset

logger = logging.getLogger(__name__)

def test_choose_preset_no_presets(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    dialog = gui_testing_utils.build_empty_dialog()

    choosepreset = component_choosepreset.ComponentChoosePreset(hypertts_instance, dialog)
    choosepreset.draw(dialog.layout())
    # check the defaults
    assert choosepreset.new_preset_radio_button.isChecked()
    assert choosepreset.new_preset == True
    # no presets are available, so the "existing preset" radio button is disabled
    assert choosepreset.existing_preset_radio_button.isEnabled() == False
    assert choosepreset.preset_combo_box.isEnabled() == False


def test_choose_preset_existing_presets(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    dialog = gui_testing_utils.build_empty_dialog()

    # create some dummy presets
    hypertts_instance.anki_utils.config[constants.CONFIG_PRESETS] = {
        'uuid_0': {'name': 'my preset 4'},
        'uuid_1': {'name': 'my preset 5'}
    }

    choosepreset = component_choosepreset.ComponentChoosePreset(hypertts_instance, dialog)
    choosepreset.draw(dialog.layout())
    # check the defaults
    assert choosepreset.new_preset_radio_button.isChecked()
    assert choosepreset.new_preset == True
    # presets are available, so the other controls should be enabled
    assert choosepreset.existing_preset_radio_button.isEnabled() == True
    assert choosepreset.preset_combo_box.isEnabled() == True

