import sys
import os
import pprint
import pytest

import aqt.qt

from test_utils import testing_utils
from test_utils import gui_testing_utils

from hypertts_addon import component_batch_preview
from hypertts_addon import component_configuration
from hypertts_addon import config_models
from hypertts_addon import servicemanager
from hypertts_addon import logging_utils
from hypertts_addon import hypertts
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import voice
from hypertts_addon import component_voiceselection
from hypertts_addon import component_source
from hypertts_addon import component_target
from hypertts_addon import component_target_easy
from hypertts_addon import component_batch
from hypertts_addon import component_text_processing
from hypertts_addon import component_realtime_source
from hypertts_addon import component_realtime_side
from hypertts_addon import component_realtime
from hypertts_addon import component_hyperttspro
from hypertts_addon import component_shortcuts
from hypertts_addon import component_errorhandling
from hypertts_addon import component_preferences
from hypertts_addon import component_presetmappingrules
from hypertts_addon import component_mappingrule
from hypertts_addon import component_easy
from hypertts_addon import component_voiceselection_easy
from hypertts_addon import component_source_easy
from hypertts_addon import component_choose_easy_advanced
from hypertts_addon import component_services_configuration

logger = logging_utils.get_test_child_logger(__name__)

def test_shortcuts_manual(qtbot):
    # HYPERTTS_SHORTCUTS_DIALOG_DEBUG=yes pytest test_components.py -k test_shortcuts_manual -s -rPP
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # instantiate dialog
    # ==================

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    shortcuts = component_shortcuts.Shortcuts(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(shortcuts.draw())

    if os.environ.get('HYPERTTS_SHORTCUTS_DIALOG_DEBUG', 'no') == 'yes':
        dialog.exec()            

def test_shortcuts_1(qtbot):
    # pytest test_components.py -k test_shortcuts_1 -s -rPP
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # instantiate dialog
    # ==================

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    shortcuts = component_shortcuts.Shortcuts(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(shortcuts.draw())

    with qtbot.waitSignal(shortcuts.editor_add_audio_key_sequence.keySequenceChanged, timeout=5000) as blocker:
        qtbot.keyClicks(shortcuts.editor_add_audio_key_sequence, 'a')
    assert model_change_callback.model.shortcut_editor_add_audio == 'A'
    assert model_change_callback.model.shortcut_editor_preview_audio == None

    with qtbot.waitSignal(shortcuts.editor_add_audio_key_sequence.keySequenceChanged, timeout=5000) as blocker:
        qtbot.mouseClick(shortcuts.editor_add_audio_clear_button, aqt.qt.Qt.MouseButton.LeftButton)
    assert model_change_callback.model.shortcut_editor_add_audio == None
    assert model_change_callback.model.shortcut_editor_preview_audio == None    

    with qtbot.waitSignal(shortcuts.editor_add_audio_key_sequence.keySequenceChanged, timeout=5000) as blocker:
        qtbot.keyClicks(shortcuts.editor_add_audio_key_sequence, 'b')
    assert model_change_callback.model.shortcut_editor_add_audio == 'B'
    assert model_change_callback.model.shortcut_editor_preview_audio == None    

    with qtbot.waitSignal(shortcuts.editor_preview_audio_key_sequence.keySequenceChanged, timeout=5000) as blocker:
        qtbot.keyClicks(shortcuts.editor_preview_audio_key_sequence, 'c')
    assert model_change_callback.model.shortcut_editor_add_audio == 'B'
    assert model_change_callback.model.shortcut_editor_preview_audio == 'C'

def test_shortcuts_load_model(qtbot):
    # pytest test_components.py -k test_shortcuts_load_model -s -rPP
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # instantiate dialog
    # ==================

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    shortcuts = component_shortcuts.Shortcuts(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(shortcuts.draw())

    # load model
    # ==========

    model = config_models.KeyboardShortcuts()
    model.shortcut_editor_add_audio = 'Ctrl+H'
    model.shortcut_editor_preview_audio = None

    shortcuts.load_model(model)

    assert shortcuts.editor_add_audio_key_sequence.keySequence().toString() == 'Ctrl+H'
    assert shortcuts.editor_preview_audio_key_sequence.keySequence().toString() == ''
    assert model_change_callback.model == None

    model = config_models.KeyboardShortcuts()
    model.shortcut_editor_add_audio = 'Ctrl+T'
    model.shortcut_editor_preview_audio = 'Ctrl+Alt+B'

    shortcuts.load_model(model)

    assert shortcuts.editor_add_audio_key_sequence.keySequence().toString() == 'Ctrl+T'
    assert shortcuts.editor_preview_audio_key_sequence.keySequence().toString() == 'Ctrl+Alt+B'
    assert model_change_callback.model == None

def test_error_handling(qtbot):
    # pytest test_components.py -k test_error_handling -s -rPP
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # instantiate dialog
    # ==================

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    error_handling = component_errorhandling.ErrorHandling(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(error_handling.draw())

    # load model
    # ==========

    model = config_models.ErrorHandling()
    model.realtime_tts_errors_dialog_type = constants.ErrorDialogType.Tooltip

    error_handling.load_model(model)

    assert error_handling.realtime_tts_errors_dialog_type.currentText() == 'Tooltip'

    # try to make changes
    # ====================

    # Change dialog type
    error_handling.realtime_tts_errors_dialog_type.setCurrentText('Nothing')
    assert model_change_callback.model.realtime_tts_errors_dialog_type == constants.ErrorDialogType.Nothing

    # Test error stats reporting checkbox
    assert error_handling.error_stats_reporting.isChecked() == True  # default should be True
    error_handling.error_stats_reporting.setChecked(False)
    assert model_change_callback.model.error_stats_reporting == False
    error_handling.error_stats_reporting.setChecked(True) 
    assert model_change_callback.model.error_stats_reporting == True


def test_preferences_manual(qtbot):
    # HYPERTTS_PREFERENCES_DIALOG_DEBUG=yes pytest test_components.py -k test_preferences_manual -s -rPP
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # instantiate dialog
    # ==================

    preferences = component_preferences.ComponentPreferences(hypertts_instance, dialog)
    preferences.draw(dialog.getLayout())    

    if os.environ.get('HYPERTTS_PREFERENCES_DIALOG_DEBUG', 'no') == 'yes':
        dialog.exec()            



def test_preferences_save(qtbot):
    # pytest test_components.py -k test_preferences_1 -s -rPP
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # instantiate dialog
    # ==================

    preferences = component_preferences.ComponentPreferences(hypertts_instance, dialog)
    preferences.draw(dialog.getLayout())    

    # button state checks
    # ===================

    assert preferences.save_button.isEnabled() == False

    # change a keyboard shortcut
    with qtbot.waitSignal(preferences.shortcuts.editor_add_audio_key_sequence.keySequenceChanged, timeout=5000) as blocker:
        qtbot.keyClicks(preferences.shortcuts.editor_add_audio_key_sequence, 'a')

    with qtbot.waitSignal(preferences.shortcuts.editor_preview_audio_key_sequence.keySequenceChanged, timeout=5000) as blocker:
        qtbot.keyClicks(preferences.shortcuts.editor_preview_audio_key_sequence, 'c')

    assert preferences.save_button.isEnabled() == True

    # change the realtime tts dialog type
    preferences.error_handling.realtime_tts_errors_dialog_type.setCurrentText('Tooltip')

    # click save
    qtbot.mouseClick(preferences.save_button, aqt.qt.Qt.MouseButton.LeftButton)

    # make sure config was saved
    assert constants.CONFIG_KEYBOARD_SHORTCUTS in hypertts_instance.anki_utils.written_config[constants.CONFIG_PREFERENCES]

    assert hypertts_instance.anki_utils.written_config[constants.CONFIG_PREFERENCES][constants.CONFIG_KEYBOARD_SHORTCUTS]['shortcut_editor_add_audio'] == 'A'
    assert hypertts_instance.anki_utils.written_config[constants.CONFIG_PREFERENCES]['error_handling']['realtime_tts_errors_dialog_type'] == 'Tooltip'

    # try to deserialize
    deserialized_preferences = hypertts_instance.deserialize_preferences(hypertts_instance.anki_utils.written_config[constants.CONFIG_PREFERENCES])
    assert deserialized_preferences.keyboard_shortcuts.shortcut_editor_add_audio == 'A'
    assert deserialized_preferences.keyboard_shortcuts.shortcut_editor_preview_audio == 'C'


def test_preferences_load(qtbot):
    # pytest test_components.py -k test_preferences_load -s -rPP
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # instantiate dialog
    # ==================

    preferences = component_preferences.ComponentPreferences(hypertts_instance, dialog)

    preferences_model = config_models.Preferences()
    preferences_model.keyboard_shortcuts.shortcut_editor_add_audio = 'Ctrl+H'
    preferences_model.keyboard_shortcuts.shortcut_editor_preview_audio = 'Alt+P'

    # button state checks
    # ===================

    preferences.load_model(preferences_model)
    preferences.draw(dialog.getLayout())

    assert preferences.save_button.isEnabled() == False

    assert preferences.shortcuts.editor_add_audio_key_sequence.keySequence().toString() == 'Ctrl+H'
    assert preferences.shortcuts.editor_preview_audio_key_sequence.keySequence().toString() == 'Alt+P'


def test_choose_easy_advanced_default(qtbot):
    """Test that Easy mode is selected by default"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    def dialog_input_sequence(dialog):    
        # just click OK with default selection (Easy mode)
        qtbot.mouseClick(dialog.button_box.button(aqt.qt.QDialogButtonBox.StandardButton.Ok), 
                        aqt.qt.Qt.MouseButton.LeftButton)

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_CHDOOSE_EASY_ADVANCED] = dialog_input_sequence
    result = component_choose_easy_advanced.show_easy_advanced_dialog(hypertts_instance)
    assert result == config_models.EasyAdvancedMode.EASY

def test_choose_easy_advanced_select_advanced(qtbot):
    """Test selecting Advanced mode"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    def dialog_input_sequence(dialog):    
        # select Advanced mode
        dialog.advanced_radio.setChecked(True)
        # click OK
        qtbot.mouseClick(dialog.button_box.button(aqt.qt.QDialogButtonBox.StandardButton.Ok), 
                        aqt.qt.Qt.MouseButton.LeftButton)

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_CHDOOSE_EASY_ADVANCED] = dialog_input_sequence
    result = component_choose_easy_advanced.show_easy_advanced_dialog(hypertts_instance)
    assert result == config_models.EasyAdvancedMode.ADVANCED

def test_choose_easy_advanced_cancel(qtbot):
    """Test canceling the dialog"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    def dialog_input_sequence(dialog):    
        # click Cancel
        qtbot.mouseClick(dialog.button_box.button(aqt.qt.QDialogButtonBox.StandardButton.Cancel), 
                        aqt.qt.Qt.MouseButton.LeftButton)

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_CHDOOSE_EASY_ADVANCED] = dialog_input_sequence
    result = component_choose_easy_advanced.show_easy_advanced_dialog(hypertts_instance)
    assert result == None

def test_choose_easy_advanced_close(qtbot):
    """Test closing the dialog"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    def dialog_input_sequence(dialog):    
        # simulate clicking the X button
        dialog.reject()

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_CHDOOSE_EASY_ADVANCED] = dialog_input_sequence
    result = component_choose_easy_advanced.show_easy_advanced_dialog(hypertts_instance)
    assert result == None

def test_ensure_easy_advanced_choice_not_made(qtbot):
    """Test ensuring choice when user hasn't chosen yet"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    def dialog_input_sequence(dialog):    
        # select Advanced mode
        dialog.advanced_radio.setChecked(True)
        # click OK
        qtbot.mouseClick(dialog.button_box.button(aqt.qt.QDialogButtonBox.StandardButton.Ok), 
                        aqt.qt.Qt.MouseButton.LeftButton)

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_CHDOOSE_EASY_ADVANCED] = dialog_input_sequence

    # User hasn't made a choice yet
    configuration = hypertts_instance.get_configuration()
    configuration.user_choice_easy_advanced = False
    hypertts_instance.save_configuration(configuration)
    # clear config updates (make sure the assert works later)
    del hypertts_instance.anki_utils.written_config[constants.CONFIG_CONFIGURATION]    

    # Should show dialog and save choice
    return_value = component_choose_easy_advanced.ensure_easy_advanced_choice_made(hypertts_instance)
    assert return_value == True

    # Verify configuration was updated
    assert hypertts_instance.anki_utils.written_config[constants.CONFIG_CONFIGURATION]['user_choice_easy_advanced'] == True

    # Verify mapping rules were updated for Advanced mode
    assert hypertts_instance.anki_utils.written_config[constants.CONFIG_MAPPING_RULES]['use_easy_mode'] == False

def test_ensure_easy_advanced_choice_already_made(qtbot):
    """Test ensuring choice when user has already chosen"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    # User has already made a choice
    configuration = hypertts_instance.get_configuration()
    configuration.user_choice_easy_advanced = True
    hypertts_instance.save_configuration(configuration)

    # Should not show dialog or update anything
    return_value = component_choose_easy_advanced.ensure_easy_advanced_choice_made(hypertts_instance)
    assert return_value == True

    # Verify no configuration was written
    # assert constants.CONFIG_CONFIGURATION not in hypertts_instance.anki_utils.written_config
    assert constants.CONFIG_MAPPING_RULES not in hypertts_instance.anki_utils.written_config

def test_ensure_easy_advanced_choice_cancelled(qtbot):
    """Test ensuring choice when user cancels dialog"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    def dialog_input_sequence(dialog):    
        # Click Cancel
        qtbot.mouseClick(dialog.button_box.button(aqt.qt.QDialogButtonBox.StandardButton.Cancel), 
                        aqt.qt.Qt.MouseButton.LeftButton)

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_CHDOOSE_EASY_ADVANCED] = dialog_input_sequence

    # User hasn't made a choice yet
    configuration = hypertts_instance.get_configuration()
    configuration.user_choice_easy_advanced = False
    hypertts_instance.save_configuration(configuration)    
    # clear config updates (make sure the assert works later)
    del hypertts_instance.anki_utils.written_config[constants.CONFIG_CONFIGURATION]    

    # Should show dialog but not update anything since user cancelled
    return_value = component_choose_easy_advanced.ensure_easy_advanced_choice_made(hypertts_instance)
    assert return_value == False

    # Verify no configuration was written
    assert constants.CONFIG_CONFIGURATION not in hypertts_instance.anki_utils.written_config
    assert constants.CONFIG_MAPPING_RULES not in hypertts_instance.anki_utils.written_config

def test_choose_easy_advanced_manual(qtbot):
    # HYPERTTS_EASY_ADVANCED_DIALOG_DEBUG=yes pytest tests/test_components.py -k test_choose_easy_advanced_manual -s -rPP
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    def dialog_input_sequence(dialog):    
        if os.environ.get('HYPERTTS_EASY_ADVANCED_DIALOG_DEBUG', 'no') == 'yes':
            dialog.exec()

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_CHDOOSE_EASY_ADVANCED] = dialog_input_sequence
    component_choose_easy_advanced.show_easy_advanced_dialog(hypertts_instance)

