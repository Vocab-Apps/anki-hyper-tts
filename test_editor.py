import unittest
import pytest
import pprint
import PyQt5

import dialogs

import testing_utils
import editor_processing
import constants
import errors

def test_process_choosetranslation(qtbot):
    # pytest test_editor.py -rPP -k test_process_choosetranslation

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('batch_translation')

    mock_language_tools.cloud_language_tools.translate_all_result = {
        '老人家': {
            'serviceA': 'first translation A',
            'serviceB': 'second translation B'
        }
    }

    bridge_str = 'choosetranslation:1'

    # when the choose translation dialog comes up, we should pick serviceB
    mock_language_tools.anki_utils.display_dialog_behavior = 'choose_serviceB'

    editor = config_gen.get_mock_editor_with_note(config_gen.note_id_1)
    editor_manager = editor_processing.EditorManager(mock_language_tools)
    editor_manager.process_choosetranslation(editor,  bridge_str)

    assert len(mock_language_tools.anki_utils.editor_set_field_value_calls) == 1
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[0]['field_index'] == 1
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[0]['text'] == 'second translation B'

def test_process_choosetranslation_empty(qtbot):
    # pytest test_editor.py -s -rPP -k test_process_choosetranslation_empty

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('batch_translation')

    bridge_str = 'choosetranslation:1'

    editor = config_gen.get_mock_editor_with_note(config_gen.note_id_3)
    editor_manager = editor_processing.EditorManager(mock_language_tools)
    editor_manager.process_choosetranslation(editor,  bridge_str)

    assert len(mock_language_tools.anki_utils.editor_set_field_value_calls) == 0

    assert mock_language_tools.anki_utils.last_action == 'choosing translation'
    assert isinstance(mock_language_tools.anki_utils.last_exception, errors.LanguageToolsValidationFieldEmpty)
    

def test_process_choosetranslation_request_error(qtbot):
    # pytest test_editor.py -s -rPP -k test_process_choosetranslation_request_error

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('batch_translation')

    bridge_str = 'choosetranslation:1'

    mock_language_tools.cloud_language_tools.translation_unhandled_exception_map = {
        '老人家': 'unhandled exception translate all'
    }

    editor = config_gen.get_mock_editor_with_note(config_gen.note_id_1)
    editor_manager = editor_processing.EditorManager(mock_language_tools)
    editor_manager.process_choosetranslation(editor,  bridge_str)

    assert len(mock_language_tools.anki_utils.editor_set_field_value_calls) == 0

    assert mock_language_tools.anki_utils.last_action == 'choosing translation'
    assert isinstance(mock_language_tools.anki_utils.last_exception, Exception)
    assert str(mock_language_tools.anki_utils.last_exception) == 'unhandled exception translate all'

def test_process_choosetranslation_cancel(qtbot):
    # pytest test_editor.py -rPP -k test_process_choosetranslation_cancel

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('batch_translation')

    mock_language_tools.cloud_language_tools.translate_all_result = {
        '老人家': {
            'serviceA': 'first translation A',
            'serviceB': 'second translation B'
        }
    }

    bridge_str = 'choosetranslation:1'

    # when the choose translation dialog comes up, we should pick serviceB
    mock_language_tools.anki_utils.display_dialog_behavior = 'cancel'

    editor = config_gen.get_mock_editor_with_note(config_gen.note_id_1)
    editor_manager = editor_processing.EditorManager(mock_language_tools)
    editor_manager.process_choosetranslation(editor,  bridge_str)    

    assert len(mock_language_tools.anki_utils.editor_set_field_value_calls) == 0
    

def test_editor_translation(qtbot):
    # pytest test_editor.py -rPP -k test_editor_translation

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('batch_translation')

    mock_language_tools.cloud_language_tools.translation_map = {
        '老人': 'old people (short)',
        '电扇': 'electric fan'
    }    

    editor = config_gen.get_mock_editor_with_note(config_gen.note_id_1)
    editor_manager = editor_processing.EditorManager(mock_language_tools)

    # regular example
    # ---------------

    field_index = 0
    note_id = config_gen.note_id_1
    field_value = '老人' # short version
    bridge_str = f'key:{field_index}:{note_id}:{field_value}'
    editor_manager.process_field_update(editor, bridge_str)

    # verify outputs
    assert len(mock_language_tools.anki_utils.editor_set_field_value_calls) == 1
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[0]['field_index'] == 1
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[0]['text'] == 'old people (short)'

    # empty input
    # -----------
    field_value = '' # empty
    bridge_str = f'key:{field_index}:{note_id}:{field_value}'
    editor_manager.process_field_update(editor, bridge_str)

    # verify outputs
    assert len(mock_language_tools.anki_utils.editor_set_field_value_calls) == 2
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[1]['field_index'] == 1
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[1]['text'] == ''


    # empty input (html tag)
    # ----------------------
    field_value = '<br/>' # empty
    bridge_str = f'key:{field_index}:{note_id}:{field_value}'
    editor_manager.process_field_update(editor, bridge_str)

    # verify outputs
    assert len(mock_language_tools.anki_utils.editor_set_field_value_calls) == 3
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[2]['field_index'] == 1
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[2]['text'] == ''    

    # disable live updates
    # --------------------

    bridge_str = f'languagetools:liveupdates:false'
    editor_manager.process_command(editor, bridge_str)

    # now send another field update
    field_value = 'yoyoyyo' # short version
    bridge_str = f'key:{field_index}:{note_id}:{field_value}'
    editor_manager.process_field_update(editor, bridge_str)

    # nothing should have happened
    assert len(mock_language_tools.anki_utils.editor_set_field_value_calls) == 3

    # re-enable live updates
    bridge_str = f'languagetools:liveupdates:true'
    editor_manager.process_command(editor, bridge_str)    

    # send field update
    field_value = '老人' # short version
    bridge_str = f'key:{field_index}:{note_id}:{field_value}'
    editor_manager.process_field_update(editor, bridge_str)

    # verify outputs
    assert len(mock_language_tools.anki_utils.editor_set_field_value_calls) == 4
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[3]['field_index'] == 1
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[3]['text'] == 'old people (short)'


    # force update
    # ------------

    # disable updates again
    bridge_str = f'languagetools:liveupdates:false'
    editor_manager.process_command(editor, bridge_str)

    # force an update
    field_value = '电扇'
    bridge_str = f'languagetools:forcefieldupdate:{field_index}:{field_value}'
    editor_manager.process_command(editor, bridge_str)

    # verify outputs
    assert len(mock_language_tools.anki_utils.editor_set_field_value_calls) == 5
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[4]['field_index'] == 1
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[4]['text'] == 'electric fan'

    # change typing delay
    # -------------------

    bridge_str = f'languagetools:typingdelay:1750'
    editor_manager.process_command(editor, bridge_str)

    assert mock_language_tools.anki_utils.written_config[constants.CONFIG_LIVE_UPDATE_DELAY] == 1750
    assert editor_manager.field_change_timer.delay_ms == 1750
        



def test_editor_transliteration(qtbot):
    # pytest test_editor.py -rPP -k test_editor_transliteration

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('batch_transliteration')

    mock_language_tools.cloud_language_tools.transliteration_map = {
        '老人': 'laoren'
    }    

    editor = config_gen.get_mock_editor_with_note(config_gen.note_id_1)
    editor_manager = editor_processing.EditorManager(mock_language_tools)

    field_index = 0
    note_id = config_gen.note_id_1
    field_value = '老人' # short version
    bridge_str = f'key:{field_index}:{note_id}:{field_value}'
    editor_manager.process_field_update(editor, bridge_str)

    # verify outputs
    assert len(mock_language_tools.anki_utils.editor_set_field_value_calls) == 1
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[0]['field_index'] == 3 # pinyin
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[0]['text'] == 'laoren'

def test_editor_audio(qtbot):
    # pytest test_editor.py -rPP -k test_editor_audio

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('batch_audio')

    mock_language_tools.cloud_language_tools.transliteration_map = {
        '老人': 'laoren'
    }    

    editor = config_gen.get_mock_editor_with_note(config_gen.note_id_1)
    editor_manager = editor_processing.EditorManager(mock_language_tools)

    field_index = 0
    note_id = config_gen.note_id_1
    field_value = '老人' # short version
    bridge_str = f'key:{field_index}:{note_id}:{field_value}'
    editor_manager.process_field_update(editor, bridge_str)

    # verify outputs

    # sound should have been played
    assert mock_language_tools.anki_utils.played_sound['text'] == '老人'

    assert len(mock_language_tools.anki_utils.editor_set_field_value_calls) == 1
    assert mock_language_tools.anki_utils.editor_set_field_value_calls[0]['field_index'] == 2 # sound
    assert '.mp3' in mock_language_tools.anki_utils.editor_set_field_value_calls[0]['text']