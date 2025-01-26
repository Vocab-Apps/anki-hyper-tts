import os
import logging
import pprint
import aqt.qt

from test_utils import testing_utils
from test_utils import gui_testing_utils

from hypertts_addon import constants
from hypertts_addon import component_mappingrule
from hypertts_addon import component_presetmappingrules
from hypertts_addon import config_models
from hypertts_addon import errors

logger = logging.getLogger(__name__)


def test_component_mapping_rule_1(qtbot):
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

    # create simple preset
    preset_id = 'uuid_0'
    name = 'my preset 1'
    testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id, name=name)

    mapping_rule = config_models.MappingRule(
        preset_id='uuid_0', rule_type=constants.MappingRuleType.NoteType, enabled=True,
        automatic=False, model_id=deck_note_type.model_id, deck_id=deck_note_type.deck_id)

    dialog = gui_testing_utils.build_empty_gridlayout_dialog()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    model_delete_callback = gui_testing_utils.MockModelDeleteCallback()
    requested_started_callback = gui_testing_utils.MockRequestStartedCallback()
    requested_finished_callback = gui_testing_utils.MockRequestFinishedCallback()

    component_rule = component_mappingrule.ComponentMappingRule(hypertts_instance, 
        editor_context, model_change_callback.model_updated, model_delete_callback.model_delete,
        requested_started_callback.request_started, requested_finished_callback.request_finished)
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
            'audio_languages': ['fr_FR'],
            'name': 'voice_a_1', 
            'service': 'ServiceA',
            'voice_key': {'name': 'voice_1'},
            'service_fee': 'free'
        },
        'options': {}
    }        

    # click run button
    qtbot.mouseClick(component_rule.run_button, aqt.qt.Qt.MouseButton.LeftButton)
    # check that the audio was added correctly
    assert 'Sound' in editor_context.note.set_values
    sound_tag = editor_context.note.set_values['Sound']
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == '老人家'
    assert audio_data['voice']['voice_key'] == {'name': 'voice_1'}

def test_component_mapping_rule_use_selection_2(qtbot):
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

    # create simple preset
    preset_id = 'uuid_0'
    name = 'my preset 1'
    testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id, name=name, use_selection=True)

    mapping_rule = config_models.MappingRule(
        preset_id='uuid_0', rule_type=constants.MappingRuleType.NoteType, enabled=True,
        automatic=False, model_id=deck_note_type.model_id, deck_id=deck_note_type.deck_id)

    dialog = gui_testing_utils.build_empty_gridlayout_dialog()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    model_delete_callback = gui_testing_utils.MockModelDeleteCallback()
    requested_started_callback = gui_testing_utils.MockRequestStartedCallback()
    requested_finished_callback = gui_testing_utils.MockRequestFinishedCallback()

    component_rule = component_mappingrule.ComponentMappingRule(hypertts_instance, 
        editor_context, model_change_callback.model_updated, model_delete_callback.model_delete,
        requested_started_callback.request_started, requested_finished_callback.request_finished)
    component_rule.draw(dialog.getLayout(), 0)
    component_rule.load_model(mapping_rule)

    assert component_rule.preset_name_label.text() == 'my preset 1'

    assert component_rule.rule_type_note_type.isChecked() == True
    assert component_rule.enabled_checkbox.isChecked() == True


    # set selection
    editor_context.selected_text = '老'

    # click preview button
    qtbot.mouseClick(component_rule.preview_button, aqt.qt.Qt.MouseButton.LeftButton)
    # check that the audio played is correct

    assert hypertts_instance.anki_utils.played_sound == {
        'source_text': '老',
        'voice': {
            'gender': 'Male', 
            'audio_languages': ['fr_FR'],
            'name': 'voice_a_1', 
            'service': 'ServiceA',
            'voice_key': {'name': 'voice_1'},
            'service_fee': 'free'
        },
        'options': {}
    }        



def test_component_preset_mapping_rules_1(qtbot):
    # pytest --log-cli-level=DEBUG test_component_presetmappingrules.py -k test_component_preset_mapping_rules_1

    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

    # create simple preset
    preset_id = 'uuid_0'
    preset_name = 'my preset 42'
    testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id, name=preset_name)
    
    def dialog_input_sequence(dialog):
        assert dialog.mapping_rules.note_type_label.text() == 'Chinese Words'
        assert dialog.mapping_rules.deck_name_label.text() == 'deck 1'
        
        # initially, the save button is disabled
        assert dialog.mapping_rules.save_button.isEnabled() == False

        # we shouldn't have any rules
        assert len(dialog.mapping_rules.get_model().rules) == 0

        # patch the "choose_preset" function
        def mock_choose_preset():
            return preset_id
        dialog.mapping_rules.choose_preset = mock_choose_preset

        # press the "add rule" button
        qtbot.mouseClick(dialog.mapping_rules.add_rule_button, aqt.qt.Qt.MouseButton.LeftButton)

        # check that model got updated
        assert len(dialog.mapping_rules.get_model().rules) == 1
        assert dialog.mapping_rules.get_model().rules[0].preset_id == preset_id

        # make sure that the rule is displayed
        # find all labels inside 
        preset_name_label_0 = dialog.findChild(aqt.qt.QLabel, 'preset_name_label_0')
        assert preset_name_label_0.text() == preset_name

        # ensure save button is enabled
        assert dialog.mapping_rules.save_button.isEnabled() == True

        # click the save button
        logger.info('clicking the save button')
        qtbot.mouseClick(dialog.mapping_rules.save_button, aqt.qt.Qt.MouseButton.LeftButton)

        pprint.pprint(hypertts_instance.anki_utils.written_config)

        # make sure the preset mapping rules got saved
        assert constants.CONFIG_MAPPING_RULES in hypertts_instance.anki_utils.written_config
        
        # load the rules and do some checks
        mapping_rules = hypertts_instance.load_mapping_rules()

        assert len(mapping_rules.rules) == 1

        # save button should have closed the dialog
        assert dialog.closed == True
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_PRESET_MAPPING_RULES] = dialog_input_sequence    
    component_presetmappingrules.create_dialog(hypertts_instance, deck_note_type, editor_context)

    # re-open the dialog, and disable the rule
    def dialog_input_sequence_2(dialog):
        # we should have one rule now
        assert len(dialog.mapping_rules.get_model().rules) == 1
        # the preset name should be displayed
        preset_name_label_0 = dialog.findChild(aqt.qt.QLabel, 'preset_name_label_0')
        assert preset_name_label_0.text() == preset_name
        # the save button should be disabled, we didn't change anything
        assert dialog.mapping_rules.save_button.isEnabled() == False

        # uncheck the "enabled" checkbox
        logger.info('marking enabled checkbox as disabled')
        enabled_checkbox_0 = dialog.findChild(aqt.qt.QCheckBox, 'enabled_checkbox_0')
        enabled_checkbox_0.setChecked(False)

        # save button should be enabled now
        assert dialog.mapping_rules.save_button.isEnabled() == True

    logger.debug('re-opening dialog')
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_PRESET_MAPPING_RULES] = dialog_input_sequence_2
    component_presetmappingrules.create_dialog(hypertts_instance, deck_note_type, editor_context)        

    # re-open the dialog and delete the rule
    def dialog_input_sequence_3(dialog):
        # we should have one rule now
        assert len(dialog.mapping_rules.get_model().rules) == 1
        # the preset name should be displayed
        preset_name_label_0 = dialog.findChild(aqt.qt.QLabel, 'preset_name_label_0')
        assert preset_name_label_0.text() == preset_name
        # the save button should be disabled, we didn't change anything
        assert dialog.mapping_rules.save_button.isEnabled() == False

        # delete the rule
        delete_button = dialog.findChild(aqt.qt.QPushButton, 'delete_rule_button_0')
        assert delete_button != None
        qtbot.mouseClick(delete_button, aqt.qt.Qt.MouseButton.LeftButton)
        # we shouldn't have any rules
        assert len(dialog.mapping_rules.get_model().rules) == 0
        # save button should be enabled
        assert dialog.mapping_rules.save_button.isEnabled() == True
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_PRESET_MAPPING_RULES] = dialog_input_sequence_3
    component_presetmappingrules.create_dialog(hypertts_instance, deck_note_type, editor_context)        

def test_component_preset_mapping_rules_cancel_2(qtbot):
    # pytest --log-cli-level=DEBUG test_component_presetmappingrules.py -k test_component_preset_mapping_rules_1
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

    def dialog_input_sequence(dialog):
        assert dialog.mapping_rules.note_type_label.text() == 'Chinese Words'
        assert dialog.mapping_rules.deck_name_label.text() == 'deck 1'
        
        # initially, the save button is disabled
        assert dialog.mapping_rules.save_button.isEnabled() == False

        # we shouldn't have any rules
        assert len(dialog.mapping_rules.get_model().rules) == 0

        # patch the "choose_preset" function
        def mock_choose_preset():
            return None
        dialog.mapping_rules.choose_preset = mock_choose_preset

        # press the "add rule" button
        qtbot.mouseClick(dialog.mapping_rules.add_rule_button, aqt.qt.Qt.MouseButton.LeftButton)

        # we still shouldn't have any rules
        assert len(dialog.mapping_rules.get_model().rules) == 0    
        assert dialog.mapping_rules.save_button.isEnabled() == False

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_PRESET_MAPPING_RULES] = dialog_input_sequence
    component_presetmappingrules.create_dialog(hypertts_instance, deck_note_type, editor_context)                

    
def test_component_preset_mapping_rules_cancel_button_3(qtbot):
    # pytest --log-cli-level=DEBUG test_component_presetmappingrules.py -k test_component_preset_mapping_rules_1

    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

    # create simple preset
    preset_id = 'uuid_0'
    preset_name = 'my preset 42'
    testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id, name=preset_name)
    
    def dialog_input_sequence(dialog):
        assert dialog.mapping_rules.note_type_label.text() == 'Chinese Words'
        assert dialog.mapping_rules.deck_name_label.text() == 'deck 1'
        
        # press the cancel button
        qtbot.mouseClick(dialog.mapping_rules.cancel_button, aqt.qt.Qt.MouseButton.LeftButton)

        # dialog should be closed
        assert dialog.closed == True

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_PRESET_MAPPING_RULES] = dialog_input_sequence    
    component_presetmappingrules.create_dialog(hypertts_instance, deck_note_type, editor_context)



def test_component_preset_mapping_rules_manual_4(qtbot):
    # HYPERTTS_DIALOG_DEBUG=yes pytest --log-cli-level=DEBUG test_component_presetmappingrules.py -k test_component_preset_mapping_rules_manual_4

    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

    # create simple preset
    preset_id_1 = 'uuid_0'
    preset_name = 'my preset 42'
    testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id_1, name=preset_name)

    preset_id_2 = 'uuid_1'
    preset_name = 'my preset 43'
    testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id_2, name=preset_name)    

    preset_id_3 = 'uuid_2'
    preset_name = 'my preset 44'
    testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id_3, name=preset_name)
    
    def dialog_input_sequence(dialog):
        # patch the "choose_preset" function

        # add preset 1
        def mock_choose_preset():
            return preset_id_1
        dialog.mapping_rules.choose_preset = mock_choose_preset
        qtbot.mouseClick(dialog.mapping_rules.add_rule_button, aqt.qt.Qt.MouseButton.LeftButton)

        # add preset 2
        def mock_choose_preset():
            return preset_id_2
        dialog.mapping_rules.choose_preset = mock_choose_preset
        qtbot.mouseClick(dialog.mapping_rules.add_rule_button, aqt.qt.Qt.MouseButton.LeftButton)

        # add preset 3
        def mock_choose_preset():
            return preset_id_3
        dialog.mapping_rules.choose_preset = mock_choose_preset
        qtbot.mouseClick(dialog.mapping_rules.add_rule_button, aqt.qt.Qt.MouseButton.LeftButton)                

        # display dialog
        if os.environ.get('HYPERTTS_DIALOG_DEBUG', 'no') == 'yes':
            dialog.exec()

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_PRESET_MAPPING_RULES] = dialog_input_sequence    
    component_presetmappingrules.create_dialog(hypertts_instance, deck_note_type, editor_context)


def test_component_preset_mapping_rules_add_then_disable_1(qtbot):
    # pytest --log-cli-level=DEBUG test_component_presetmappingrules.py -k test_component_preset_mapping_rules_add_then_disable_1

    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

    # create two presets
    preset_id_1 = 'uuid_0'
    preset_name_1 = 'my preset 42'
    testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id_1, name=preset_name_1)
    preset_id_2 = 'uuid_1'
    preset_name_2 = 'my preset 43'
    testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id_2, name=preset_name_2)
    
    def dialog_input_sequence(dialog):
        assert dialog.mapping_rules.note_type_label.text() == 'Chinese Words'
        assert dialog.mapping_rules.deck_name_label.text() == 'deck 1'
        
        # add two presets

        def mock_choose_preset_1():
            return preset_id_1
        dialog.mapping_rules.choose_preset = mock_choose_preset_1
        qtbot.mouseClick(dialog.mapping_rules.add_rule_button, aqt.qt.Qt.MouseButton.LeftButton)

        def mock_choose_preset_2():
            return preset_id_2
        dialog.mapping_rules.choose_preset = mock_choose_preset_2
        qtbot.mouseClick(dialog.mapping_rules.add_rule_button, aqt.qt.Qt.MouseButton.LeftButton)        

        # make sure that the rule is displayed
        # find all labels inside 
        preset_name_label_0 = dialog.findChild(aqt.qt.QLabel, 'preset_name_label_0')
        assert preset_name_label_0.text() == preset_name_1
        preset_name_label_1 = dialog.findChild(aqt.qt.QLabel, 'preset_name_label_1')
        assert preset_name_label_1.text() == preset_name_2

        # disable the second rule
        enabled_checkbox_1 = dialog.findChild(aqt.qt.QCheckBox, 'enabled_checkbox_1')
        enabled_checkbox_1.setChecked(False)

        # click the save button
        logger.info('clicking the save button')
        qtbot.mouseClick(dialog.mapping_rules.save_button, aqt.qt.Qt.MouseButton.LeftButton)

        # save button should have closed the dialog
        assert dialog.closed == True
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_PRESET_MAPPING_RULES] = dialog_input_sequence    
    component_presetmappingrules.create_dialog(hypertts_instance, deck_note_type, editor_context)

    # re-open the dialog, and disable the rule
    def dialog_input_sequence_2(dialog):
        # we should see two rules

        preset_name_label_0 = dialog.findChild(aqt.qt.QLabel, 'preset_name_label_0')
        assert preset_name_label_0.text() == preset_name_1
        preset_name_label_1 = dialog.findChild(aqt.qt.QLabel, 'preset_name_label_1')
        assert preset_name_label_1.text() == preset_name_2

    logger.debug('re-opening dialog')
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_PRESET_MAPPING_RULES] = dialog_input_sequence_2
    component_presetmappingrules.create_dialog(hypertts_instance, deck_note_type, editor_context)        

def test_component_preset_mapping_rules_preview_run(qtbot):
    # pytest --log-cli-level=DEBUG test_component_presetmappingrules.py -k test_component_preset_mapping_rules_preview_run

    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

    # create two presets
    preset_id_1 = 'uuid_0'
    preset_name_1 = 'my preset 42'
    testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id_1, name=preset_name_1)

    preset_id_2 = 'uuid_1'
    preset_name_2 = 'my preset 43'
    testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id_2, name=preset_name_2,
        target_field='Sound English')
    
    def dialog_input_sequence(dialog):

        # add two presets
        def mock_choose_preset():
            return preset_id_1
        dialog.mapping_rules.choose_preset = mock_choose_preset
        qtbot.mouseClick(dialog.mapping_rules.add_rule_button, aqt.qt.Qt.MouseButton.LeftButton)

        def mock_choose_preset():
            return preset_id_2
        dialog.mapping_rules.choose_preset = mock_choose_preset
        qtbot.mouseClick(dialog.mapping_rules.add_rule_button, aqt.qt.Qt.MouseButton.LeftButton)

        # click preview button
        qtbot.mouseClick(dialog.mapping_rules.preview_all_button, aqt.qt.Qt.MouseButton.LeftButton)
        expected_sound_played = {
            'source_text': '老人家',
            'voice': {
                'gender': 'Male', 
                'audio_languages': ['fr_FR'], 
                'name': 'voice_a_1', 
                'service': 'ServiceA',
                'voice_key': {'name': 'voice_1'},
                'service_fee': 'free'
            },
            'options': {}
        }
        assert hypertts_instance.anki_utils.all_played_sounds[0] == expected_sound_played
        assert hypertts_instance.anki_utils.all_played_sounds[1] == expected_sound_played

        # click the run all button
        qtbot.mouseClick(dialog.mapping_rules.run_all_button, aqt.qt.Qt.MouseButton.LeftButton)
        
        # check that sound was applied to note
        assert 'Sound' in editor_context.note.set_values
        sound_tag = editor_context.note.set_values['Sound']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)
        assert audio_data['source_text'] == '老人家'


        assert 'Sound English' in editor_context.note.set_values
        sound_tag = editor_context.note.set_values['Sound English']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)
        assert audio_data['source_text'] == '老人家'



    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_PRESET_MAPPING_RULES] = dialog_input_sequence    
    component_presetmappingrules.create_dialog(hypertts_instance, deck_note_type, editor_context)



def test_component_preset_mapping_rules_deleted_preset(qtbot):
    # pytest --log-cli-level=DEBUG tests/test_component_presetmappingrules.py -k test_component_preset_mapping_rules_deleted_preset

    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

    # create simple preset
    preset_id = 'uuid_0'
    preset_name = 'my preset 42'
    testing_utils.create_simple_batch(hypertts_instance, preset_id=preset_id, name=preset_name)
    
    def dialog_input_sequence(dialog):
        # patch the "choose_preset" function
        def mock_choose_preset():
            return preset_id
        dialog.mapping_rules.choose_preset = mock_choose_preset

        # add preset
        qtbot.mouseClick(dialog.mapping_rules.add_rule_button, aqt.qt.Qt.MouseButton.LeftButton)

        # make sure that the rule is displayed
        preset_name_label_0 = dialog.findChild(aqt.qt.QLabel, 'preset_name_label_0')
        assert preset_name_label_0.text() == preset_name

        # click save button
        qtbot.mouseClick(dialog.mapping_rules.save_button, aqt.qt.Qt.MouseButton.LeftButton)

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_PRESET_MAPPING_RULES] = dialog_input_sequence    
    component_presetmappingrules.create_dialog(hypertts_instance, deck_note_type, editor_context)

    # now delete the preset
    hypertts_instance.delete_preset(preset_id)

    # re-open dialog and try to edit the now-deleted preset
    def dialog_input_sequence_2(dialog):
        # find the edit button
        edit_button = dialog.findChild(aqt.qt.QPushButton, 'edit_button_0')
        assert edit_button != None

        # verify preset shows as unknown
        preset_name_label_0 = dialog.findChild(aqt.qt.QLabel, 'preset_name_label_0')
        assert preset_name_label_0.text() == constants.GUI_TEXT_UNKNOWN_PRESET

        # click edit button, should raise PresetNotFound
        qtbot.mouseClick(edit_button, aqt.qt.Qt.MouseButton.LeftButton)

        # verify error was shown
        assert isinstance(hypertts_instance.anki_utils.last_exception, errors.PresetNotFound)
        # it should be handled, should be a known exception 
        assert hypertts_instance.anki_utils.last_exception_is_known == True

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_PRESET_MAPPING_RULES] = dialog_input_sequence_2
    component_presetmappingrules.create_dialog(hypertts_instance, deck_note_type, editor_context)

def test_component_preset_mapping_easy_mode(qtbot):
    # pytest --log-cli-level=DEBUG tests/test_component_presetmappingrules.py -k test_component_preset_mapping_easy_mode

    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

    def dialog_input_sequence_initial(dialog):
        # assert that easy_mode_checkbox is unchecked
        assert dialog.mapping_rules.easy_mode_checkbox.isChecked() == False
        # now check it
        dialog.mapping_rules.easy_mode_checkbox.setChecked(True)
        # click save and close
        qtbot.mouseClick(dialog.mapping_rules.save_button, aqt.qt.Qt.MouseButton.LeftButton)

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_PRESET_MAPPING_RULES] = dialog_input_sequence_initial
    component_presetmappingrules.create_dialog(hypertts_instance, deck_note_type, editor_context)

    def dialog_input_sequence_2(dialog):
        # assert that easy_mode_checkbox is checked
        assert dialog.mapping_rules.easy_mode_checkbox.isChecked() == True
        # now uncheck it
        dialog.mapping_rules.easy_mode_checkbox.setChecked(False)
        # click save and close
        qtbot.mouseClick(dialog.mapping_rules.save_button, aqt.qt.Qt.MouseButton.LeftButton)        

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_PRESET_MAPPING_RULES] = dialog_input_sequence_2
    component_presetmappingrules.create_dialog(hypertts_instance, deck_note_type, editor_context)

    def dialog_input_sequence_3(dialog):
        # assert that easy_mode_checkbox is unchecked
        assert dialog.mapping_rules.easy_mode_checkbox.isChecked() == False

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_PRESET_MAPPING_RULES] = dialog_input_sequence_3
    component_presetmappingrules.create_dialog(hypertts_instance, deck_note_type, editor_context)    
