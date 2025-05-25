import os
import aqt.qt
import pprint
import copy

from test_utils import testing_utils
from test_utils import gui_testing_utils

from hypertts_addon import constants
from hypertts_addon import component_batch
from hypertts_addon import component_easy
from hypertts_addon import config_models
from hypertts_addon import logging_utils

logger = logging_utils.get_test_child_logger(__name__)


def select_default_voice(voices_combobox):
    testing_utils.voice_selection_voice_list_select('voice_a_1', 'ServiceA', voices_combobox)

def test_batch_dialog_editor_manual(qtbot):
    # HYPERTTS_BATCH_DIALOG_DEBUG=yes pytest --log-cli-level=DEBUG test_components.py -k test_batch_dialog_editor_manual -s -rPP
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()
    def batch_dialog_input_sequence(dialog):
        if os.environ.get('HYPERTTS_BATCH_DIALOG_DEBUG', 'no') == 'yes':
            dialog.exec()        
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = batch_dialog_input_sequence    
    component_batch.create_dialog_editor_new_preset(hypertts_instance, editor_context)

def test_batch_dialog_editor_preview_apply(qtbot):
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

    def batch_dialog_input_sequence(dialog):
        # select second voice
        select_default_voice(dialog.batch_component.voice_selection.voices_combobox)

        # test sound preview
        # ==================
        # dialog.exec()
        qtbot.mouseClick(dialog.batch_component.preview_sound_button, aqt.qt.Qt.MouseButton.LeftButton)
        assert hypertts_instance.anki_utils.played_sound == {
            'source_text': '老人家',
            'voice': {
                'gender': 'Male', 
                'audio_languages': ['fr_FR'],
                'name': 'voice_a_1', 
                'service': 'ServiceA',
                'service_fee': 'free',
                'voice_key': {'name': 'voice_1'}
            },
            'options': {}
        }    

        # test apply to note
        # ==================
        # dialog.exec()
        
        # set target field
        dialog.batch_component.target.target_field_combobox.setCurrentText('Sound')

        # apply not note
        qtbot.mouseClick(dialog.batch_component.apply_button, aqt.qt.Qt.MouseButton.LeftButton)

        sound_tag = editor_context.note.set_values['Sound']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

        assert audio_data['source_text'] == '老人家'

        assert editor_context.editor.set_note_called == True

        # undo is disabled in this workflow, just use the undo from update_note call
        # assert hypertts_instance.anki_utils.undo_started == True
        # assert hypertts_instance.anki_utils.undo_finished == True

        assert dialog.closed == True

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = batch_dialog_input_sequence
    component_batch.create_dialog_editor_new_preset(hypertts_instance, editor_context)



def test_batch_dialog_editor_last_saved(qtbot):
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()
    def batch_dialog_input_sequence(dialog):
        # select second voice
        select_default_voice(dialog.batch_component.voice_selection.voices_combobox)

        # set preset name and save
        # set profile name
        preset_name = 'new editor preset 1'
        hypertts_instance.anki_utils.ask_user_get_text_response = preset_name
        qtbot.mouseClick(dialog.batch_component.profile_rename_button, aqt.qt.Qt.MouseButton.LeftButton)
        # click save button
        qtbot.mouseClick(dialog.batch_component.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)

        assert dialog.batch_component.last_saved_preset_id == 'uuid_1'
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = batch_dialog_input_sequence
    component_batch.create_dialog_editor_new_preset(hypertts_instance, editor_context)        

def test_batch_dialog_editor_save_and_close(qtbot):
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()
    def batch_dialog_input_sequence(dialog):
        # select second voice
        select_default_voice(dialog.batch_component.voice_selection.voices_combobox)

        # set preset name and save
        # set profile name
        preset_name = 'new editor preset 1'
        hypertts_instance.anki_utils.ask_user_get_text_response = preset_name
        qtbot.mouseClick(dialog.batch_component.profile_rename_button, aqt.qt.Qt.MouseButton.LeftButton)

        # click save and close button
        qtbot.mouseClick(dialog.batch_component.profile_save_and_close_button, aqt.qt.Qt.MouseButton.LeftButton)

        assert dialog.batch_component.last_saved_preset_id == 'uuid_1'    

        assert dialog.closed == True
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = batch_dialog_input_sequence
    component_batch.create_dialog_editor_new_preset(hypertts_instance, editor_context)        


def test_batch_dialog_editor_create_then_load(qtbot):
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()
    preset_uuid = 'uuid_1'
    def batch_dialog_input_sequence(dialog):
        # select second voice
        select_default_voice(dialog.batch_component.voice_selection.voices_combobox)

        # set preset name and save
        # set profile name
        preset_name = 'editor preset 1'
        hypertts_instance.anki_utils.ask_user_get_text_response = preset_name
        qtbot.mouseClick(dialog.batch_component.profile_rename_button, aqt.qt.Qt.MouseButton.LeftButton)
        # save
        qtbot.mouseClick(dialog.batch_component.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)

        # close the dialog
        dialog.close()

        # make sure the preset was saved
        assert preset_uuid in hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS]

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = batch_dialog_input_sequence
    component_batch.create_dialog_editor_new_preset(hypertts_instance, editor_context)                

    def batch_dialog_input_sequence_2(dialog):
        # test sound preview
        # ==================
        # dialog.exec()
        qtbot.mouseClick(dialog.batch_component.preview_sound_button, aqt.qt.Qt.MouseButton.LeftButton)
        assert hypertts_instance.anki_utils.played_sound == {
            'source_text': '老人家',
            'voice': {
                'gender': 'Male', 
                'audio_languages': ['fr_FR'],
                'name': 'voice_a_1', 
                'service': 'ServiceA',
                'service_fee': 'free',
                'voice_key': {'name': 'voice_1'}
            },
            'options': {}
        }    


        # test apply to note
        # ==================
        
        # set target field
        dialog.batch_component.target.target_field_combobox.setCurrentText('Sound')

        # apply not note
        qtbot.mouseClick(dialog.batch_component.apply_button, aqt.qt.Qt.MouseButton.LeftButton)

        sound_tag = editor_context.note.set_values['Sound']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

        assert audio_data['source_text'] == '老人家'

        assert editor_context.editor.set_note_called == True

        # undo is disabled in this workflow
        # assert hypertts_instance.anki_utils.undo_started == True
        # assert hypertts_instance.anki_utils.undo_finished == True

        assert dialog.closed == True    

    # now, open the dialog, with the existing preset
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = batch_dialog_input_sequence_2
    component_batch.create_dialog_editor_existing_preset(hypertts_instance, editor_context, preset_uuid)

def test_batch_dialog_editor_sound_sample(qtbot):
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()
    def batch_dialog_input_sequence(dialog):
        dialog.batch_component.source.source_field_combobox.setCurrentText('English')
        select_default_voice(dialog.batch_component.voice_selection.voices_combobox)

        # test sound preview for the voice
        # ================================

        assert dialog.batch_component.voice_selection.play_sample_button.isEnabled() == True

        qtbot.mouseClick(dialog.batch_component.preview_sound_button, aqt.qt.Qt.MouseButton.LeftButton)
        assert hypertts_instance.anki_utils.played_sound == {
            'source_text': 'old people',
            'voice': {
                'gender': 'Male', 
                'audio_languages': ['fr_FR'],
                'name': 'voice_a_1', 
                'service': 'ServiceA',
                'service_fee': 'free',
                'voice_key': {'name': 'voice_1'}
            },
            'options': {}
        }    
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = batch_dialog_input_sequence
    component_batch.create_dialog_editor_new_preset(hypertts_instance, editor_context)

def test_batch_dialog_editor_template_error(qtbot):
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()
    def batch_dialog_input_sequence(dialog):
        # select template mode and enter incorrect advanced template
        dialog.batch_component.source.batch_mode_combobox.setCurrentText('advanced_template')
        # enter template format
        # qtbot.keyClicks(batch.source.advanced_template_input, """field_1 = 'yoyo'""")
        dialog.batch_component.source.advanced_template_input.setPlainText("""field_1 = 'yoyo'""")

        # ensure the preview label is showing an error
        label_error_text = dialog.batch_component.preview.source_preview_label.text()
        expected_label_text = """<b>Encountered Error:</b> No "result" variable found. You must assign the final template output to a result variable."""
        assert label_error_text == expected_label_text
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = batch_dialog_input_sequence
    component_batch.create_dialog_editor_new_preset(hypertts_instance, editor_context)

def test_editor_get_new_preset_id_1(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    note = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    mock_editor = testing_utils.MockEditor()
    editor_context = config_models.EditorContext(
        note=note, 
        editor=mock_editor, 
        add_mode=False, 
        selected_text=None, 
        current_field=None,
        clipboard=None)

    # user cancels
    def dialog_input_sequence(dialog):
        # user presses cancel button
        qtbot.mouseClick(dialog.batch_component.cancel_button, aqt.qt.Qt.MouseButton.LeftButton)
    # don't automatically save
    hypertts_instance.anki_utils.ask_user_bool_response = False
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    preset_id = component_batch.create_dialog_editor_new_preset(hypertts_instance, editor_context)
    assert preset_id == None

    # user selections English source field then saves
    def dialog_input_sequence(dialog):
        dialog.batch_component.source.source_field_combobox.setCurrentText('English')
        # user presses cancel button
        qtbot.mouseClick(dialog.batch_component.profile_save_and_close_button, aqt.qt.Qt.MouseButton.LeftButton)
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    preset_id = component_batch.create_dialog_editor_new_preset(hypertts_instance, editor_context)
    assert preset_id != None
    # load the preset, make sure source field is English
    preset = hypertts_instance.load_preset(preset_id)
    assert preset.source.source_field == 'English'

    # user selections English source field then saves, but ultimately cancels
    def dialog_input_sequence(dialog):
        dialog.batch_component.source.source_field_combobox.setCurrentText('English')
        # click save button
        qtbot.mouseClick(dialog.batch_component.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)
        # user presses cancel button
        qtbot.mouseClick(dialog.batch_component.cancel_button, aqt.qt.Qt.MouseButton.LeftButton)
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    preset_id = component_batch.create_dialog_editor_new_preset(hypertts_instance, editor_context)
    assert preset_id == None

def test_batch_dialog_editor_advanced_template_rename(qtbot):
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

    advanced_template_text = """
    field_1 = 'yoyo'
    result = field_1"""
    preset_uuid = 'uuid_1'

    # step one, create advanced template
    # ==================================

    def batch_dialog_input_sequence_create(dialog):
        # select template mode and enter incorrect advanced template
        dialog.batch_component.source.batch_mode_combobox.setCurrentText('advanced_template')
        # enter template format
        # qtbot.keyClicks(batch.source.advanced_template_input, """field_1 = 'yoyo'""")
        dialog.batch_component.source.advanced_template_input.setPlainText(advanced_template_text)

        # set preset name and save
        # set profile name
        preset_name_1 = 'adv template preset 1'
        hypertts_instance.anki_utils.ask_user_get_text_response = preset_name_1
        qtbot.mouseClick(dialog.batch_component.profile_rename_button, aqt.qt.Qt.MouseButton.LeftButton)
        # click save button
        qtbot.mouseClick(dialog.batch_component.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)

        # make sure the preset was saved
        assert preset_uuid in hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS]

        # logger.debug(pprint.pformat(hypertts_instance.anki_utils.written_config))
        assert hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS][preset_uuid]['source']['source_template'] == advanced_template_text


    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = batch_dialog_input_sequence_create
    component_batch.create_dialog_editor_new_preset(hypertts_instance, editor_context)
    
    # now, open the dialog, with the existing preset

    def batch_dialog_input_sequence_load(dialog):
        # make sure advanced template text is corect
        assert dialog.batch_component.source.advanced_template_input.toPlainText() == advanced_template_text

        # now rename again
        preset_name_2 = 'adv template preset 2'
        hypertts_instance.anki_utils.ask_user_get_text_response = preset_name_2
        logger.info('clicking rename button')
        qtbot.mouseClick(dialog.batch_component.profile_rename_button, aqt.qt.Qt.MouseButton.LeftButton)
        assert dialog.batch_component.source.advanced_template_input.toPlainText() == advanced_template_text

        # click save button
        logger.info('clicking save button')
        qtbot.mouseClick(dialog.batch_component.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)
        assert dialog.batch_component.source.advanced_template_input.toPlainText() == advanced_template_text

        # make sure the preset was saved
        assert preset_uuid in hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS]

        logger.debug(pprint.pformat(hypertts_instance.anki_utils.written_config))
        assert hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS][preset_uuid]['source']['source_template'] == advanced_template_text

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = batch_dialog_input_sequence_load
    component_batch.create_dialog_editor_existing_preset(hypertts_instance, editor_context, preset_uuid)

def test_batch_dialog_editor_advanced_template_save_button(qtbot):
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

    advanced_template_text = """
    field_1 = 'yoyo'
    result = field_1"""
    preset_uuid = 'uuid_1'

    # step one, create advanced template
    # ==================================

    def batch_dialog_input_sequence_create(dialog):
        # select template mode and enter incorrect advanced template
        dialog.batch_component.source.batch_mode_combobox.setCurrentText('advanced_template')
        # enter template format
        # qtbot.keyClicks(batch.source.advanced_template_input, """field_1 = 'yoyo'""")
        dialog.batch_component.source.advanced_template_input.setPlainText(advanced_template_text)

        # set preset name and save
        # set profile name
        preset_name_1 = 'adv template preset 1'
        hypertts_instance.anki_utils.ask_user_get_text_response = preset_name_1
        qtbot.mouseClick(dialog.batch_component.profile_rename_button, aqt.qt.Qt.MouseButton.LeftButton)
        # click save button
        qtbot.mouseClick(dialog.batch_component.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)

        # make sure the preset was saved
        assert preset_uuid in hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS]

        # logger.debug(pprint.pformat(hypertts_instance.anki_utils.written_config))
        assert hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS][preset_uuid]['source']['source_template'] == advanced_template_text


    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = batch_dialog_input_sequence_create
    component_batch.create_dialog_editor_new_preset(hypertts_instance, editor_context)
    
    # now, open the dialog, with the existing preset

    def batch_dialog_input_sequence_load(dialog):
        # make sure advanced template text is corect
        assert dialog.batch_component.source.advanced_template_input.toPlainText() == advanced_template_text

        # save button should not be enabled
        assert dialog.batch_component.profile_save_button.isEnabled() == False

        # the current displayed stack should be advanced template
        assert dialog.batch_component.source.source_config_stack.currentIndex() == dialog.batch_component.source.SOURCE_CONFIG_STACK_ADVANCED_TEMPLATE

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = batch_dialog_input_sequence_load
    component_batch.create_dialog_editor_existing_preset(hypertts_instance, editor_context, preset_uuid)    

def test_easy_dialog_editor_manual_field_text(qtbot):
    # HYPERTTS_EASY_DIALOG_DEBUG=yes pytest --log-cli-level=DEBUG tests/test_components.py -k test_easy_dialog_editor_manual -s -rPP
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()
    def easy_dialog_input_sequence(dialog):
        if os.environ.get('HYPERTTS_EASY_DIALOG_DEBUG', 'no') == 'yes':
            dialog.exec()        
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_EASY] = easy_dialog_input_sequence
    component_easy.create_dialog_editor_new_preset(hypertts_instance, deck_note_type, editor_context)

def test_easy_dialog_editor_manual_clipboard_selected(qtbot):
    # HYPERTTS_EASY_DIALOG_DEBUG=yes pytest --log-cli-level=DEBUG tests/test_components.py -k test_easy_dialog_editor_manual_clipboard_selected -s -rPP
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()
    editor_context.clipboard = 'clipboard text'
    editor_context.selected_text = 'selected text'
    def easy_dialog_input_sequence(dialog):
        if os.environ.get('HYPERTTS_EASY_DIALOG_DEBUG', 'no') == 'yes':
            dialog.exec()        
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_EASY] = easy_dialog_input_sequence
    component_easy.create_dialog_editor_new_preset(hypertts_instance, deck_note_type, editor_context)


def test_easy_dialog_editor_1(qtbot):
    # pytest --log-cli-level=DEBUG tests/test_component_batch_editor.py -k test_easy_dialog_editor_1 -s -rPP
    # full end to end test for easy dialog started from the editor

    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()
    def easy_dialog_input_sequence_inital_state(dialog):
        # check source field value
        assert dialog.easy_component.source.source_text_edit.toPlainText() == '老人家'
        # the right side widget should be hidden
        assert dialog.easy_component.right_widget.isHidden() == True
        # the toggle_settings_button button should show "More Settings"
        assert dialog.easy_component.toggle_settings_button.text() == constants.GUI_TEXT_EASY_BUTTON_MORE_SETTINGS
        
        # voice selection assertions
                
        # languages_combobox should have All, English, French, Japanese
        # extract text of all items
        languages = [dialog.easy_component.voice_selection.languages_combobox.itemText(i) for i in range(dialog.easy_component.voice_selection.languages_combobox.count())]
        assert languages == ['All', '', 'English', 'French', 'Japanese']
        assert dialog.easy_component.voice_selection.languages_combobox.count() == 5 # including separator
        assert dialog.easy_component.voice_selection.languages_combobox.currentText() == 'All'

        # services_combobox should have All, ServiceA, ServiceB
        services = [dialog.easy_component.voice_selection.services_combobox.itemText(i) for i in range(dialog.easy_component.voice_selection.services_combobox.count())]
        assert services == ['All', '', 'ServiceA', 'ServiceB']
        assert dialog.easy_component.voice_selection.services_combobox.count() == 4 # including separator

        # now expand the "more settings"
        qtbot.mouseClick(dialog.easy_component.toggle_settings_button, aqt.qt.Qt.MouseButton.LeftButton)
        assert dialog.easy_component.right_widget.isHidden() == False
        # the toggle_settings_button button should show "Hide Settings"
        assert dialog.easy_component.toggle_settings_button.text() == constants.GUI_TEXT_EASY_BUTTON_HIDE_MORE_SETTINGS

        # check target settings
        # same field should be selected
        assert dialog.easy_component.target.same_field_group.checkedButton() == dialog.easy_component.target.radio_button_same_field
        # radio_button_after should be selected
        assert dialog.easy_component.target.insert_location_group.checkedButton() == dialog.easy_component.target.radio_button_after

        # model checks
        # ============
        assert dialog.easy_component.batch_model != None
        assert dialog.easy_component.batch_model.name != None
        assert dialog.easy_component.batch_model.text_processing != None
        # the target_field is temporarily incorrect in the target model, but that's OK
        # assert dialog.easy_component.batch_model.target.target_field == None

        # now check the main dialog's get_model function, it should have the target field set
        assert dialog.easy_component.get_model().target.target_field == 'Chinese'


    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_EASY] = easy_dialog_input_sequence_inital_state
    component_easy.create_dialog_editor_new_preset(hypertts_instance, deck_note_type, editor_context)    


    # check sound preview
    # ===================
    def easy_dialog_input_sequence_sound_preview(dialog):
        # select second voice
        select_default_voice(dialog.easy_component.voice_selection.voices_combobox)

        # test sound preview
        # ==================
        # dialog.exec()
        qtbot.mouseClick(dialog.easy_component.preview_sound_button, aqt.qt.Qt.MouseButton.LeftButton)
        assert hypertts_instance.anki_utils.played_sound == {
            'source_text': '老人家',
            'voice': {
                'gender': 'Male', 
                'audio_languages': ['fr_FR'],
                'name': 'voice_a_1', 
                'service': 'ServiceA',
                'service_fee': 'free',
                'voice_key': {'name': 'voice_1'}
            },
            'options': {}
        }    

        # override the text
        dialog.easy_component.source.source_text_edit.setPlainText('custom text')
        qtbot.mouseClick(dialog.easy_component.preview_sound_button, aqt.qt.Qt.MouseButton.LeftButton)
        assert hypertts_instance.anki_utils.played_sound == {
            'source_text': 'custom text',
            'voice': {
                'gender': 'Male',
                'audio_languages': ['fr_FR'],
                'name': 'voice_a_1', 
                'service': 'ServiceA',
                'service_fee': 'free',
                'voice_key': {'name': 'voice_1'}
            },
            'options': {}
        }

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_EASY] = easy_dialog_input_sequence_sound_preview
    component_easy.create_dialog_editor_new_preset(hypertts_instance, deck_note_type, editor_context)

    # add audio to note
    # =================

    def easy_dialog_input_sequence_add_audio(dialog):
        # select second voice
        select_default_voice(dialog.easy_component.voice_selection.voices_combobox)

        # apply audio
        # ===========

        qtbot.mouseClick(dialog.easy_component.add_audio_button, aqt.qt.Qt.MouseButton.LeftButton)

        # check that sound tag was set
        sound_tag = editor_context.note.set_values['Chinese']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

        assert audio_data['source_text'] == '老人家'

        assert editor_context.editor.set_note_called == True

        assert dialog.closed == True

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_EASY] = easy_dialog_input_sequence_add_audio
    component_easy.create_dialog_editor_new_preset(hypertts_instance, deck_note_type, editor_context)

    def easy_dialog_input_sequence_overwrite_text_add_audio(dialog):
        # select second voice
        select_default_voice(dialog.easy_component.voice_selection.voices_combobox)

        # overwrite input text
        dialog.easy_component.source.source_text_edit.setPlainText('custom text')


        # apply audio
        # ===========

        qtbot.mouseClick(dialog.easy_component.add_audio_button, aqt.qt.Qt.MouseButton.LeftButton)

        # check that sound tag was set
        sound_tag = editor_context.note.set_values['Chinese']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

        assert audio_data['source_text'] == 'custom text'

        assert editor_context.editor.set_note_called == True

        assert dialog.closed == True

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_EASY] = easy_dialog_input_sequence_overwrite_text_add_audio
    component_easy.create_dialog_editor_new_preset(hypertts_instance, deck_note_type, editor_context)    


def test_easy_dialog_editor_2(qtbot):
    # pytest --log-cli-level=DEBUG tests/test_component_batch_editor.py -k test_easy_dialog_editor_2 -s -rPP
    # full end to end test for easy dialog started from the editor

    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()
    # modify the editor context to remove the current field (no field selected)
    editor_context.current_field = None


    # first, create the preset
    batch_config = config_models.BatchConfig(hypertts_instance.anki_utils)
    batch_config.name = 'default'
    source = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='English')
    target = config_models.BatchTarget(target_field='English', same_field=True)
    text_processing = config_models.TextProcessing()

    #  preset 1
    voice_list = hypertts_instance.service_manager.full_voice_list()    
    voice_a_3 = [x for x in voice_list if x.name == 'voice_a_3'][0].voice_id
    voice_selection = config_models.VoiceSelectionSingle()
    voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_3, {}))

    batch_config.set_source(source)
    batch_config.set_target(target)
    batch_config.set_voice_selection(voice_selection)
    batch_config.set_text_processing(text_processing)

    # save the preset
    hypertts_instance.save_preset(batch_config)    

    preset_uuid = batch_config.uuid

    def easy_dialog_input_sequence_load_preset(dialog):
        # check source field value
        assert dialog.easy_component.source.field_combobox.currentData() == 'English'
        assert dialog.easy_component.source.source_text_edit.toPlainText() == 'old people'
        # check voice selection
        # Verify the correct voice is selected
        selected_voice_text = dialog.easy_component.voice_selection.voices_combobox.currentText()
        assert 'voice_a_3' in selected_voice_text
        assert 'ServiceA' in selected_voice_text        


    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_EASY] = easy_dialog_input_sequence_load_preset
    component_easy.create_dialog_editor_existing_preset(hypertts_instance, deck_note_type, editor_context, preset_uuid)

def test_easy_dialog_editor_3(qtbot):
    # pytest --log-cli-level=DEBUG tests/test_component_batch_editor.py -k test_easy_dialog_editor_3 -s -rPP
    # full end to end test for easy dialog started from the editor

    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()

    def easy_dialog_input_sequence_close(dialog):
        # press the cancel button
        qtbot.mouseClick(dialog.easy_component.cancel_button, aqt.qt.Qt.MouseButton.LeftButton)
        # check that dialog was closed
        assert dialog.closed == True


    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_EASY] = easy_dialog_input_sequence_close
    component_easy.create_dialog_editor_new_preset(hypertts_instance, deck_note_type, editor_context)

def test_easy_dialog_editor_4_save_load_default_preset(qtbot):
    # pytest --log-cli-level=DEBUG tests/test_component_batch_editor.py -k test_easy_dialog_editor_4_save_load_default_preset -s -rPP
    # full end to end test for easy dialog started from the editor

    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()
    # ensure there's no field selected
    editor_context.current_field = None

    # run once , and change the source field

    def easy_dialog_input_sequence_apply_close(dialog):
        # check that the source field selected is English
        assert dialog.easy_component.source.field_combobox.currentData() == 'Chinese'
        # select the English field
        logger.debug(f'setting source field to English')
        field_index = dialog.easy_component.source.field_combobox.findData('English')
        assert field_index != -1
        dialog.easy_component.source.field_combobox.setCurrentIndex(field_index)
        # press the add audio button
        logger.debug(f'clicking add audio button')
        qtbot.mouseClick(dialog.easy_component.add_audio_button, aqt.qt.Qt.MouseButton.LeftButton)

        # ensure that sound has been applied
        # check that sound tag was set
        assert 'English' in editor_context.note.set_values
        sound_tag = editor_context.note.set_values['English']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)
        assert audio_data['source_text'] == 'old people'
        assert editor_context.editor.set_note_called == True

        # check that dialog was closed
        assert dialog.closed == True

        # after this, the default profile should have been saved


    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_EASY] = easy_dialog_input_sequence_apply_close
    component_easy.create_dialog_editor(hypertts_instance, deck_note_type, editor_context)

    def easy_dialog_input_sequence_load(dialog):
        # this time, because we loaded a profile previously, the source field should be English
        assert dialog.easy_component.source.field_combobox.currentData() == 'English'

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_EASY] = easy_dialog_input_sequence_load
    component_easy.create_dialog_editor(hypertts_instance, deck_note_type, editor_context)    

def test_easy_dialog_editor_5_default_add_then_select(qtbot):
    # pytest --log-cli-level=DEBUG tests/test_component_batch_editor.py -k test_easy_dialog_editor_5_default_add_then_select -s -rPP
    # Test that selection is prioritized over field text when available

    logger.debug(f'START test_easy_dialog_editor_5_default_add_then_select')

    # First, create a context with cursor in Chinese field
    hypertts_instance, deck_note_type, editor_context = gui_testing_utils.get_editor_context()
    editor_context.current_field = 'Chinese'
    
    # First dialog: add audio with Chinese field selected
    def easy_dialog_input_sequence_add_audio(dialog):
        # Verify Text from field radio is selected with Chinese field
        assert dialog.easy_component.source.field_radio.isChecked() == True
        assert dialog.easy_component.source.field_combobox.currentData() == 'Chinese'
        assert dialog.easy_component.source.source_text_edit.toPlainText() == '老人家'
        
        # Add audio
        logger.debug(f'adding audio for field Chinese')
        qtbot.mouseClick(dialog.easy_component.add_audio_button, aqt.qt.Qt.MouseButton.LeftButton)
        
        # Verify dialog closed
        assert dialog.closed == True

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_EASY] = easy_dialog_input_sequence_add_audio
    component_easy.create_dialog_editor(hypertts_instance, deck_note_type, editor_context)

    logger.debug(f'finished initial step, by now the default preset should be saved with Chinese field text')
    logger.debug(f'prepare dialog with selection in English field')

    # Now create a new context with selected text in English field
    editor_context_with_selection = copy.deepcopy(editor_context)
    editor_context_with_selection.current_field = 'English'
    editor_context_with_selection.selected_text = 'old people'  # Full content of English field
    
    # Second dialog: verify selection is prioritized
    def easy_dialog_input_sequence_verify_selection(dialog):
        logger.debug(f'entering dialog input fn, easy_dialog_input_sequence_verify_selection')

        # Verify Selected text radio is selected
        assert dialog.easy_component.source.selection_radio.isChecked() == True
        assert dialog.easy_component.source.field_radio.isChecked() == False
        
        # Field combobox should show English, because that's the field we selected from
        assert dialog.easy_component.source.field_combobox.currentData() == 'English'
        assert dialog.easy_component.source.field_combobox.isEnabled() == False
        
        # Text should be the selected text
        assert dialog.easy_component.source.source_text_edit.toPlainText() == 'old people'
        
        # Add audio 
        logger.debug('clicking add audio button, the expectation is to generate audio into the English field')
        qtbot.mouseClick(dialog.easy_component.add_audio_button, aqt.qt.Qt.MouseButton.LeftButton)
        
        # Verify sound was added to the English field
        assert 'English' in editor_context_with_selection.note.set_values
        sound_tag = editor_context_with_selection.note.set_values['English']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)
        assert audio_data['source_text'] == 'old people'
        assert editor_context_with_selection.editor.set_note_called == True
        
        # Verify dialog closed
        assert dialog.closed == True

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_EASY] = easy_dialog_input_sequence_verify_selection
    component_easy.create_dialog_editor(hypertts_instance, deck_note_type, editor_context_with_selection)
