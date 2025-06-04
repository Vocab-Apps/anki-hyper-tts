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

def test_services_configuration_default_trial(qtbot):
    """Test that Trial mode is selected when clicking the trial button"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    def dialog_input_sequence(dialog):    
        # click the trial button
        qtbot.mouseClick(dialog.trial_button, aqt.qt.Qt.MouseButton.LeftButton)

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_SERVICES_CONFIGURATION] = dialog_input_sequence
    result = component_services_configuration.show_services_configuration_dialog(hypertts_instance)
    assert result == config_models.ServicesConfigurationMode.TRIAL

def test_services_configuration_select_free_services(qtbot):
    """Test selecting Free Services mode"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    def dialog_input_sequence(dialog):    
        # click the free services button
        qtbot.mouseClick(dialog.free_services_button, aqt.qt.Qt.MouseButton.LeftButton)

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_SERVICES_CONFIGURATION] = dialog_input_sequence
    result = component_services_configuration.show_services_configuration_dialog(hypertts_instance)
    assert result == config_models.ServicesConfigurationMode.FREE_SERVICES

def test_services_configuration_select_manual(qtbot):
    """Test selecting Manual Configuration mode"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    def dialog_input_sequence(dialog):    
        # click the manual configuration button
        qtbot.mouseClick(dialog.manual_button, aqt.qt.Qt.MouseButton.LeftButton)

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_SERVICES_CONFIGURATION] = dialog_input_sequence
    result = component_services_configuration.show_services_configuration_dialog(hypertts_instance)
    assert result == config_models.ServicesConfigurationMode.MANUAL_CONFIGURATION

def test_services_configuration_cancel(qtbot):
    """Test canceling the services configuration dialog"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    def dialog_input_sequence(dialog):    
        # click Cancel
        qtbot.mouseClick(dialog.cancel_button, aqt.qt.Qt.MouseButton.LeftButton)

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_SERVICES_CONFIGURATION] = dialog_input_sequence
    result = component_services_configuration.show_services_configuration_dialog(hypertts_instance)
    assert result == None

def test_services_configuration_close(qtbot):
    """Test closing the services configuration dialog"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    def dialog_input_sequence(dialog):    
        # simulate clicking the X button
        dialog.reject()

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_SERVICES_CONFIGURATION] = dialog_input_sequence
    result = component_services_configuration.show_services_configuration_dialog(hypertts_instance)
    assert result == None

def test_services_configuration_manual(qtbot):
    # HYPERTTS_SERVICES_CONFIG_DIALOG_DEBUG=yes pytest tests/test_components.py -k test_services_configuration_manual -s -rPP
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    def dialog_input_sequence(dialog):    
        if os.environ.get('HYPERTTS_SERVICES_CONFIG_DIALOG_DEBUG', 'no') == 'yes':
            dialog.exec()

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_SERVICES_CONFIGURATION] = dialog_input_sequence
    component_services_configuration.show_services_configuration_dialog(hypertts_instance)
