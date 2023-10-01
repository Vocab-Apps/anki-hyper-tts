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
import component_batch

logger = logging.getLogger(__name__)


def test_batch_dialog_editor_manual(qtbot):
    # HYPERTTS_BATCH_DIALOG_DEBUG=yes pytest --log-cli-level=DEBUG test_components.py -k test_batch_dialog_editor_manual -s -rPP

    logger.info('test_batch_dialog_editor_manual')

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    

    # test saving of config
    # =====================

    dialog = gui_testing_utils.build_empty_dialog()
    note = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    mock_editor = testing_utils.MockEditor()
    dialog = gui_testing_utils.build_empty_dialog()
    batch = component_batch.create_component_batch_editor_new_preset(
        hypertts_instance, dialog, note, mock_editor, False, 'preset 1')
    
    if os.environ.get('HYPERTTS_BATCH_DIALOG_DEBUG', 'no') == 'yes':
        dialog.exec()

def test_batch_dialog_editor(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    
    note = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)

    mock_editor = testing_utils.MockEditor()

    dialog = gui_testing_utils.build_empty_dialog()
    batch = component_batch.create_component_batch_editor_new_preset(
        hypertts_instance, dialog, note, mock_editor, False, 'preset 1')

    # select second voice
    batch.voice_selection.voices_combobox.setCurrentIndex(1)

    # test sound preview
    # ==================
    # dialog.exec()
    qtbot.mouseClick(batch.preview_sound_button, aqt.qt.Qt.MouseButton.LeftButton)
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


    # test apply to note
    # ==================
    # dialog.exec()
    
    # set target field
    batch.target.target_field_combobox.setCurrentText('Sound')

    # apply not note
    qtbot.mouseClick(batch.apply_button, aqt.qt.Qt.MouseButton.LeftButton)

    sound_tag = note.set_values['Sound']
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == '老人家'

    assert mock_editor.set_note_called == True

    assert hypertts_instance.anki_utils.undo_started == True
    assert hypertts_instance.anki_utils.undo_finished == True

    assert dialog.closed == True

def test_batch_dialog_editor_last_saved(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    
    note = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)

    mock_editor = testing_utils.MockEditor()

    dialog = gui_testing_utils.build_empty_dialog()
    batch = component_batch.create_component_batch_editor_new_preset(
        hypertts_instance, dialog, note, mock_editor, False, 'preset 1')

    # select second voice
    batch.voice_selection.voices_combobox.setCurrentIndex(1)

    # set preset name and save
    # set profile name
    preset_name = 'new editor preset 1'
    hypertts_instance.anki_utils.ask_user_get_text_response = preset_name
    qtbot.mouseClick(batch.profile_rename_button, aqt.qt.Qt.MouseButton.LeftButton)
    # click save button
    qtbot.mouseClick(batch.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)

    assert batch.last_saved_preset_id == 'uuid_1'



def test_batch_dialog_editor_create_then_load(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    
    note = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)

    mock_editor = testing_utils.MockEditor()

    dialog = gui_testing_utils.build_empty_dialog()
    batch = component_batch.create_component_batch_editor_new_preset(
        hypertts_instance, dialog, note, mock_editor, False, 'preset 1')

    # select second voice
    batch.voice_selection.voices_combobox.setCurrentIndex(1)

    # set preset name and save
    # set profile name
    preset_name = 'editor preset 1'
    hypertts_instance.anki_utils.ask_user_get_text_response = preset_name
    qtbot.mouseClick(batch.profile_rename_button, aqt.qt.Qt.MouseButton.LeftButton)
    # save
    qtbot.mouseClick(batch.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)

    # close the dialog
    dialog.close()

    # make sure the preset was saved
    preset_uuid = 'uuid_1'
    assert preset_uuid in hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS]

    # now, open the dialog, with the existing preset
    dialog = gui_testing_utils.build_empty_dialog()
    batch = component_batch.create_component_batch_editor_existing_preset(
        hypertts_instance, dialog, note, mock_editor, False, preset_uuid)

    # test sound preview
    # ==================
    # dialog.exec()
    qtbot.mouseClick(batch.preview_sound_button, aqt.qt.Qt.MouseButton.LeftButton)
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


    # test apply to note
    # ==================
    
    # set target field
    batch.target.target_field_combobox.setCurrentText('Sound')

    # apply not note
    qtbot.mouseClick(batch.apply_button, aqt.qt.Qt.MouseButton.LeftButton)

    sound_tag = note.set_values['Sound']
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == '老人家'

    assert mock_editor.set_note_called == True

    assert hypertts_instance.anki_utils.undo_started == True
    assert hypertts_instance.anki_utils.undo_finished == True

    assert dialog.closed == True    

def test_batch_dialog_editor_sound_sample(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    
    note = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)

    mock_editor = testing_utils.MockEditor()

    dialog = gui_testing_utils.build_empty_dialog()
    batch = component_batch.create_component_batch_editor_new_preset(
        hypertts_instance, dialog, note, mock_editor, False, 'preset 1')

    batch.source.source_field_combobox.setCurrentText('English')

    batch.voice_selection.voices_combobox.setCurrentIndex(1)

    # test sound preview for the voice
    # ================================

    assert batch.voice_selection.play_sample_button.isEnabled() == True

    qtbot.mouseClick(batch.preview_sound_button, aqt.qt.Qt.MouseButton.LeftButton)
    assert hypertts_instance.anki_utils.played_sound == {
        'source_text': 'old people',
        'voice': {
            'gender': 'Male', 
            'language': 'fr_FR', 
            'name': 'voice_a_1', 
            'service': 'ServiceA',
            'voice_key': {'name': 'voice_1'}
        },
        'options': {}
    }    



def test_batch_dialog_editor_template_error(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    
    note = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)

    mock_editor = testing_utils.MockEditor()

    dialog = gui_testing_utils.build_empty_dialog()
    batch = component_batch.create_component_batch_editor_new_preset(
        hypertts_instance, dialog, note, mock_editor, False, 'preset 1')

    # select template mode and enter incorrect advanced template
    batch.source.batch_mode_combobox.setCurrentText('advanced_template')
    # enter template format
    # qtbot.keyClicks(batch.source.advanced_template_input, """field_1 = 'yoyo'""")
    batch.source.advanced_template_input.setPlainText("""field_1 = 'yoyo'""")

    # ensure the preview label is showing an error
    label_error_text = batch.preview.source_preview_label.text()
    expected_label_text = """<b>Encountered Error:</b> No "result" variable found. You must assign the final template output to a result variable."""
    assert label_error_text == expected_label_text

    # dialog.exec()
