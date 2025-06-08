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
from hypertts_addon import component_trialsignup

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

def test_trial_signup_manual(qtbot):
    # HYPERTTS_TRIAL_SIGNUP_DIALOG_DEBUG=yes pytest tests/test_components_4.py -k test_trial_signup_manual -s -rPP
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    
    if os.environ.get('HYPERTTS_TRIAL_SIGNUP_DIALOG_DEBUG', 'no') == 'yes':
        component_trialsignup.show_trial_signup_dialog(hypertts_instance)

def test_trial_signup_component_initialization(qtbot):
    """Test that the trial signup component initializes correctly"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    
    model_changes = []
    def model_change_callback(model):
        model_changes.append(model)
    
    component = component_trialsignup.TrialSignup(hypertts_instance, model_change_callback)
    
    # Test initial model
    model = component.get_model()
    assert model.success == False
    assert model.error == None
    assert model.api_key == None

def test_trial_signup_component_draw(qtbot):
    """Test that the trial signup component draws correctly"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    
    model_changes = []
    def model_change_callback(model):
        model_changes.append(model)
    
    component = component_trialsignup.TrialSignup(hypertts_instance, model_change_callback)
    
    # Create a test dialog to hold the component
    dialog = gui_testing_utils.EmptyDialog()
    vlayout = aqt.qt.QVBoxLayout()
    
    # Draw the component
    component.draw(vlayout)
    
    dialog.setLayout(vlayout)
    
    # Verify UI elements exist
    assert hasattr(component, 'trial_email_input')
    assert hasattr(component, 'trial_password_input')
    assert hasattr(component, 'trial_validation_label')
    assert hasattr(component, 'signup_button')

def test_trial_signup_validation_empty_email(qtbot):
    """Test validation when email is empty"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    
    model_changes = []
    def model_change_callback(model):
        model_changes.append(model)
    
    component = component_trialsignup.TrialSignup(hypertts_instance, model_change_callback)
    
    # Create a test dialog to hold the component
    dialog = gui_testing_utils.EmptyDialog()
    vlayout = aqt.qt.QVBoxLayout()
    component.draw(vlayout)
    dialog.setLayout(vlayout)
    
    # Set password but leave email empty
    component.trial_password_input.setText("testpassword")
    
    # Click signup button
    qtbot.mouseClick(component.signup_button, aqt.qt.Qt.MouseButton.LeftButton)
    
    # Check validation message
    assert "Please enter an email address" in component.trial_validation_label.text()

def test_trial_signup_validation_empty_password(qtbot):
    """Test validation when password is empty"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    
    model_changes = []
    def model_change_callback(model):
        model_changes.append(model)
    
    component = component_trialsignup.TrialSignup(hypertts_instance, model_change_callback)
    
    # Create a test dialog to hold the component
    dialog = gui_testing_utils.EmptyDialog()
    vlayout = aqt.qt.QVBoxLayout()
    component.draw(vlayout)
    dialog.setLayout(vlayout)
    
    # Set email but leave password empty
    component.trial_email_input.setText("test@example.com")
    
    # Click signup button
    qtbot.mouseClick(component.signup_button, aqt.qt.Qt.MouseButton.LeftButton)
    
    # Check validation message
    assert "Please enter a password" in component.trial_validation_label.text()

def test_trial_signup_successful_saves_api_key(qtbot):
    """Test that successful trial signup saves the API key to configuration"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    
    # Mock the CloudLanguageTools to return a successful trial response
    def mock_request_trial_key(email, password, client_uuid):
        return config_models.TrialRequestReponse(
            success=True,
            api_key="trial_key",
            error=None
        )
    
    hypertts_instance.service_manager.cloudlanguagetools.request_trial_key = mock_request_trial_key
    
    model_changes = []
    def model_change_callback(model):
        model_changes.append(model)
    
    component = component_trialsignup.TrialSignup(hypertts_instance, model_change_callback)
    
    # Create a test dialog to hold the component and draw it
    dialog = gui_testing_utils.EmptyDialog()
    vlayout = aqt.qt.QVBoxLayout()
    component.draw(vlayout)
    dialog.setLayout(vlayout)
    
    # Enter email and password
    component.trial_email_input.setText("valid@email.com")
    component.trial_password_input.setText("passw@rd1")
    
    # Click signup button to trigger the trial signup
    qtbot.mouseClick(component.signup_button, aqt.qt.Qt.MouseButton.LeftButton)
    
    # Verify the API key was saved to configuration
    configuration = hypertts_instance.get_configuration()
    assert configuration.hypertts_pro_api_key == "trial_key"
    assert configuration.use_vocabai_api == True
    
    # Verify the configuration was written to storage
    assert hypertts_instance.anki_utils.written_config is not None
    assert 'configuration' in hypertts_instance.anki_utils.written_config
    written_config = hypertts_instance.anki_utils.written_config['configuration']
    assert written_config['hypertts_pro_api_key'] == "trial_key"
    assert written_config['use_vocabai_api'] == True
    
    # Verify the model was updated
    assert component.get_model().success == True
    assert component.get_model().api_key == "trial_key"

def test_trial_signup_email_verification_screen(qtbot):
    """Test that successful trial signup shows email verification screen"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    
    # Mock the CloudLanguageTools to return a successful trial response
    def mock_request_trial_key(email, password, client_uuid):
        return config_models.TrialRequestReponse(
            success=True,
            api_key="trial_key",
            error=None
        )
    
    hypertts_instance.service_manager.cloudlanguagetools.request_trial_key = mock_request_trial_key
    
    model_changes = []
    def model_change_callback(model):
        model_changes.append(model)
    
    component = component_trialsignup.TrialSignup(hypertts_instance, model_change_callback)
    
    # Create a test dialog to hold the component and draw it
    dialog = gui_testing_utils.EmptyDialog()
    vlayout = aqt.qt.QVBoxLayout()
    component.draw(vlayout)
    dialog.setLayout(vlayout)
    
    # Verify we start on signup screen (index 0)
    assert component.stacked_widget.currentIndex() == 0
    
    # Enter email and password
    component.trial_email_input.setText("test@example.com")
    component.trial_password_input.setText("password123")
    
    # Click signup button to trigger the trial signup
    qtbot.mouseClick(component.signup_button, aqt.qt.Qt.MouseButton.LeftButton)
    
    # Verify we switched to verification screen (index 1)
    assert component.stacked_widget.currentIndex() == 1
    
    # Verify verification screen elements exist
    assert hasattr(component, 'verification_description_label')
    assert hasattr(component, 'verification_status_label')
    assert hasattr(component, 'check_status_button')
    
    # Verify description contains the email
    assert "test@example.com" in component.verification_description_label.text()

def test_trial_signup_check_verification_status(qtbot):
    """Test checking email verification status"""
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    
    # Mock the CloudLanguageTools methods
    def mock_request_trial_key(email, password, client_uuid):
        return config_models.TrialRequestReponse(
            success=True,
            api_key="trial_key",
            error=None
        )
    
    def mock_check_email_verification_status(email):
        return True  # Email is verified
    
    hypertts_instance.service_manager.cloudlanguagetools.request_trial_key = mock_request_trial_key
    hypertts_instance.service_manager.cloudlanguagetools.check_email_verification_status = mock_check_email_verification_status
    
    model_changes = []
    def model_change_callback(model):
        model_changes.append(model)
    
    component = component_trialsignup.TrialSignup(hypertts_instance, model_change_callback)
    
    # Create a test dialog to hold the component and draw it
    dialog = gui_testing_utils.EmptyDialog()
    vlayout = aqt.qt.QVBoxLayout()
    component.draw(vlayout)
    dialog.setLayout(vlayout)
    
    # Complete signup first to get to verification screen
    component.trial_email_input.setText("test@example.com")
    component.trial_password_input.setText("password123")
    qtbot.mouseClick(component.signup_button, aqt.qt.Qt.MouseButton.LeftButton)
    
    # Now test the check status functionality
    qtbot.mouseClick(component.check_status_button, aqt.qt.Qt.MouseButton.LeftButton)
    
    # Verify the status message shows email is verified
    assert "Email verified!" in component.verification_status_label.text()

