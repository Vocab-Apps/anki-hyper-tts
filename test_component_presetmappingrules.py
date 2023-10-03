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
import component_presetmappingrules
import config_models

logger = logging.getLogger(__name__)


def test_component_preset_mapping_rules_1(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    # create simple preset
    preset_id = 'my preset 1'
    testing_utils.create_simple_batch(hypertts_instance, preset_id)
    
    dialog = gui_testing_utils.build_empty_dialog()
    # chinese deck
    deck_note_type: config_models.DeckNoteType = config_models.DeckNoteType(
        model_id=config_gen.model_id_chinese,
        deck_id=config_gen.deck_id)
    
    mapping_rules = component_presetmappingrules.ComponentPresetMappingRules(hypertts_instance, dialog, deck_note_type)
    mapping_rules.draw(dialog.getLayout())

    assert mapping_rules.note_type_label.text() == 'Chinese Words'
    assert mapping_rules.deck_name_label.text() == 'deck 1'

    # patch the "choose_preset" function
    def mock_choose_preset():
        return preset_id
    mapping_rules.choose_preset = mock_choose_preset

    # press the "add rule" button
    qtbot.mouseClick(mapping_rules.add_rule_button, aqt.qt.Qt.LeftButton)

    # check that model got updated
    assert len(mapping_rules.get_model().rules) == 1
    assert mapping_rules.get_model().rules[0].preset_id == preset_id