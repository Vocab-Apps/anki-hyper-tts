import sys
import os
import logging
import pprint
import aqt.qt

addon_dir = os.path.dirname(os.path.realpath(__file__))
external_dir = os.path.join(addon_dir, 'external')
sys.path.insert(0, external_dir)

import constants
import testing_utils
import gui_testing_utils
import component_mappingrule
import component_presetmappingrules
import config_models

logger = logging.getLogger(__name__)


def test_component_mapping_rule_1(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    # create simple preset
    preset_id = 'uuid_0'
    name = 'my preset 1'
    testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id, name=name)

    # hypertts_instance.anki_utils.config['presets'] = {'uuid_0': {'name': 'preset 1'} }

    model_id=config_gen.model_id_chinese
    deck_id=config_gen.deck_id
    deck_note_type: config_models.DeckNoteType = config_models.DeckNoteType(
        model_id=model_id,
        deck_id=deck_id)
    mapping_rule = config_models.MappingRule(
        preset_id='uuid_0', rule_type=constants.MappingRuleType.NoteType, enabled=True,
        automatic=False, model_id=model_id, deck_id=deck_id)

    dialog = gui_testing_utils.build_empty_gridlayout_dialog()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()

    mock_editor = testing_utils.MockEditor()
    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    mock_editor.note = note_1

    component_rule = component_mappingrule.ComponentMappingRule(hypertts_instance, 
        mock_editor, note_1, False, 0, model_change_callback.model_updated)
    component_rule.draw(dialog.getLayout(), 0)
    component_rule.load_model(mapping_rule)

    assert component_rule.preset_name_label.text() == 'my preset 1'

    assert component_rule.rule_type_note_type.isChecked() == True
    assert component_rule.enabled_checkbox.isChecked() == True

    # try modifying the rule type radio button
    logger.debug(f'clicking deck_note_type')
    component_rule.rule_type_deck_note_type.setChecked(True)
    assert model_change_callback.model.rule_type == constants.MappingRuleType.DeckNoteType
    logger.debug(f'clicking note_type')
    component_rule.rule_type_note_type.setChecked(True)
    assert model_change_callback.model.rule_type == constants.MappingRuleType.NoteType

    # try to modify the enabled checkbox
    component_rule.enabled_checkbox.setChecked(False)
    assert model_change_callback.model.enabled == False
    component_rule.enabled_checkbox.setChecked(True)
    assert model_change_callback.model.enabled == True

    # click preview button
    qtbot.mouseClick(component_rule.preview_button, aqt.qt.Qt.MouseButton.LeftButton)
    # check that the audio played is correct

    assert hypertts_instance.anki_utils.played_sound == {
        'source_text': '老人家',
        'voice': {
            'gender': 'Male', 
            'language': 'fr_FR', 
            'name': 'voice_a_1', 
            'service': 'ServiceA',
            'voice_key': {'name': 'voice_1'}
        },
        'options': {}
    }        

    # click run button
    qtbot.mouseClick(component_rule.run_button, aqt.qt.Qt.MouseButton.LeftButton)
    # check that the audio was added correctly
    assert 'Sound' in note_1.set_values
    sound_tag = note_1.set_values['Sound']
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == '老人家'
    assert audio_data['voice']['voice_key'] == {'name': 'voice_1'}
    assert note_1.flush_called == True

def test_component_preset_mapping_rules_1(qtbot):
    # pytest --log-cli-level=DEBUG test_component_presetmappingrules.py -k test_component_preset_mapping_rules_1
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    # create simple preset
    preset_id = 'uuid_0'
    preset_name = 'my preset 42'
    testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id, name=preset_name)
    
    dialog = gui_testing_utils.build_empty_dialog()
    # chinese deck
    deck_note_type: config_models.DeckNoteType = config_models.DeckNoteType(
        model_id=config_gen.model_id_chinese,
        deck_id=config_gen.deck_id)
    
    mock_editor = testing_utils.MockEditor()
    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    mock_editor.note = note_1

    mapping_rules = component_presetmappingrules.create_component(
        hypertts_instance, dialog, deck_note_type, mock_editor, note_1, False)

    assert mapping_rules.note_type_label.text() == 'Chinese Words'
    assert mapping_rules.deck_name_label.text() == 'deck 1'
    
    # initially, the save button is disabled
    assert mapping_rules.save_button.isEnabled() == False

    # we shouldn't have any rules
    assert len(mapping_rules.get_model().rules) == 0

    # patch the "choose_preset" function
    def mock_choose_preset():
        return preset_id
    mapping_rules.choose_preset = mock_choose_preset

    # press the "add rule" button
    qtbot.mouseClick(mapping_rules.add_rule_button, aqt.qt.Qt.LeftButton)

    # check that model got updated
    assert len(mapping_rules.get_model().rules) == 1
    assert mapping_rules.get_model().rules[0].preset_id == preset_id

    # make sure that the rule is displayed
    # find all labels inside 
    preset_name_label_0 = dialog.findChild(aqt.qt.QLabel, 'preset_name_label_0')
    assert preset_name_label_0.text() == preset_name

    # ensure save button is enabled
    assert mapping_rules.save_button.isEnabled() == True

    # click the save button
    logger.info('clicking the save button')
    qtbot.mouseClick(mapping_rules.save_button, aqt.qt.Qt.LeftButton)

    pprint.pprint(hypertts_instance.anki_utils.written_config)

    # make sure the preset mapping rules got saved
    assert constants.CONFIG_MAPPING_RULES in hypertts_instance.anki_utils.written_config
    
    # load the rules and do some checks
    mapping_rules = hypertts_instance.load_mapping_rules()

    assert len(mapping_rules.rules) == 1

    # save button should have closed the dialog
    assert dialog.closed == True

    # re-open the dialog
    dialog = gui_testing_utils.build_empty_dialog()
    mapping_rules = component_presetmappingrules.create_component(
        hypertts_instance, dialog, deck_note_type, mock_editor, note_1, False)
    # we should have one rule now
    assert len(mapping_rules.get_model().rules) == 1
    # the preset name should be displayed
    preset_name_label_0 = dialog.findChild(aqt.qt.QLabel, 'preset_name_label_0')
    assert preset_name_label_0.text() == preset_name    