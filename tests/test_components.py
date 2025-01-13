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
from hypertts_addon import component_easy_source

logger = logging_utils.get_test_child_logger(__name__)


def test_voice_selection_defaults_single(qtbot):
    hypertts_instance = gui_testing_utils.get_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    testing_utils.voice_selection_voice_list_select('voice_a_1', 'ServiceA', voiceselection.voices_combobox)
    expected_output = {
        'voice_selection_mode': 'single',
        'voice': {
            'voice_id': {
                'service': 'ServiceA',
                'voice_key': {'name': 'voice_1'}
            },
            'options': {
            }
        }        
    }

    assert voiceselection.serialize() == expected_output

    # dialog.exec()

def test_voice_selection_easy_defaults(qtbot):
    hypertts_instance = gui_testing_utils.get_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection_easy.VoiceSelectionEasy(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    testing_utils.voice_selection_voice_list_select('voice_a_1', 'ServiceA', voiceselection.voices_combobox)
    expected_output = {
        'voice_selection_mode': 'single',
        'voice': {
            'voice_id': {
                'service': 'ServiceA',
                'voice_key': {'name': 'voice_1'}
            },
            'options': {
            }
        }        
    }

    assert voiceselection.serialize() == expected_output

def test_voice_selection_manual(qtbot):
    # HYPERTTS_VOICE_SELECTION_DIALOG_DEBUG=yes pytest test_components.py -k test_voice_selection_manual -s -rPP
    hypertts_instance = gui_testing_utils.get_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    if os.environ.get('HYPERTTS_VOICE_SELECTION_DIALOG_DEBUG', 'no') == 'yes':
        dialog.exec()

def test_voice_selection_single_1(qtbot):
    # pytest --log-cli-level=DEBUG test_components.py -k test_voice_selection_single_1 -vv
    hypertts_instance = gui_testing_utils.get_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    testing_utils.voice_selection_voice_list_select('voice_a_2', 'ServiceA', voiceselection.voices_combobox)

    # dialog.exec()

    expected_output = {
        'voice_selection_mode': 'single',
        'voice': {
            'voice_id': {
                'service': 'ServiceA',
                'voice_key': {'name': 'voice_2'}
            },
            'options': {
            }
        }        
    }
    assert voiceselection.serialize() == expected_output    

    # change options
    speaking_rate_widget = dialog.findChild(aqt.qt.QDoubleSpinBox, "voice_option_speaking_rate")
    speaking_rate_widget.setValue(0.25)

    expected_output = {
        'voice_selection_mode': 'single',
        'voice': {
            'voice_id': {
                'service': 'ServiceA',
                'voice_key': {'name': 'voice_2'}
            },
            'options': {
                'speaking_rate': 0.25
            }
        }        
    }
    assert voiceselection.serialize() == expected_output        


def test_voice_selection_easy_single_1(qtbot):
    # pytest --log-cli-level=DEBUG tests/test_components.py -k test_voice_selection_easy_single_1 -vv
    hypertts_instance = gui_testing_utils.get_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection_easy.VoiceSelectionEasy(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    testing_utils.voice_selection_voice_list_select('voice_a_2', 'ServiceA', voiceselection.voices_combobox)

    # dialog.exec()

    expected_output = {
        'voice_selection_mode': 'single',
        'voice': {
            'voice_id': {
                'service': 'ServiceA',
                'voice_key': {'name': 'voice_2'}
            },
            'options': {
            }
        }
    }
    assert voiceselection.serialize() == expected_output

def test_voice_selection_easy_filters(qtbot):
    # pytest --log-cli-level=DEBUG tests/test_components.py -k test_voice_selection_easy_filters -vv
    hypertts_instance = gui_testing_utils.get_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection_easy.VoiceSelectionEasy(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    # ensure filters are set to All by default
    assert voiceselection.languages_combobox.currentText() == constants.LABEL_FILTER_ALL
    assert voiceselection.services_combobox.currentText() == constants.LABEL_FILTER_ALL

    # select english language filter
    voiceselection.languages_combobox.setCurrentText('English')

    # ensure japanese filter is enabled
    assert len(voiceselection.filtered_voice_list) < len(voiceselection.voice_list)
    assert len(voiceselection.filtered_voice_list) == voiceselection.voices_combobox.count()
    for voice in voiceselection.filtered_voice_list:
        assert languages.Language.en in voice.languages

    # reset to all
    voiceselection.languages_combobox.setCurrentText(constants.LABEL_FILTER_ALL)

    # ensure all voices are available now
    assert len(voiceselection.filtered_voice_list) == len(voiceselection.voice_list)

    # filter by service
    # =================
    voiceselection.services_combobox.setCurrentText('ServiceA')
    # ensure only ServiceA voices are present
    assert len(voiceselection.filtered_voice_list) < len(voiceselection.voice_list)
    assert len(voiceselection.filtered_voice_list) == voiceselection.voices_combobox.count()
    for voice in voiceselection.filtered_voice_list:
        assert voice.service == 'ServiceA'    

def test_voice_selection_easy_load_model(qtbot):
    # Test loading a voice selection model
    hypertts_instance = gui_testing_utils.get_hypertts_instance()
    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # Create a model with voice_a_1 selected
    model = config_models.VoiceSelectionSingle()
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_3'][0]
    model.set_voice(config_models.VoiceWithOptions(voice_a_1.voice_id, {}))

    # Create voice selection component and load model
    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection_easy.VoiceSelectionEasy(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())
    voiceselection.load_model(model)

    # Verify the correct voice is selected
    selected_voice_text = voiceselection.voices_combobox.currentText()
    assert 'voice_a_3' in selected_voice_text
    assert 'ServiceA' in selected_voice_text

    # Verify model is correct
    expected_output = {
        'voice_selection_mode': 'single',
        'voice': {
            'voice_id': {
                'service': 'ServiceA',
                'voice_key': {'name': 'voice_3'}
            },
            'options': {}
        }
    }
    assert voiceselection.voice_selection_model.serialize() == expected_output

def test_voice_selection_format_ogg(qtbot):
    hypertts_instance = gui_testing_utils.get_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    testing_utils.voice_selection_voice_list_select('voice_a_2', 'ServiceA', voiceselection.voices_combobox)
    # voiceselection.voices_combobox.setCurrentIndex(0) # pick second voice

    # change options
    format_widget = dialog.findChild(aqt.qt.QComboBox, "voice_option_format")

    # default should be mp3
    assert format_widget.currentText() == 'mp3'

    format_widget.setCurrentText('ogg_opus')

    expected_output = {
        'voice_selection_mode': 'single',
        'voice': {
            'voice_id': {
                'service': 'ServiceA',
                'voice_key': {'name': 'voice_2'}
            },
            'options': {
                'format': 'ogg_opus'
            }
        }        
    }
    assert voiceselection.serialize() == expected_output        

def test_voice_selection_random_1(qtbot):
    hypertts_instance = gui_testing_utils.get_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    # dialog.exec()

    # choose random mode
    # qtbot.t(voiceselection.radio_button_random, aqt.qt.Qt.MouseButton.LeftButton)
    voiceselection.radio_button_random.setChecked(True)

    # pick second voice and add it
    # voiceselection.voices_combobox.setCurrentIndex(0) # pick second voice
    testing_utils.voice_selection_voice_list_select('voice_a_2', 'ServiceA', voiceselection.voices_combobox)
    qtbot.mouseClick(voiceselection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)

    # pick third voice and add it
    # voiceselection.voices_combobox.setCurrentIndex(2) # pick second voice
    testing_utils.voice_selection_voice_list_select('voice_a_3', 'ServiceA', voiceselection.voices_combobox)
    qtbot.mouseClick(voiceselection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)    

    expected_output = {
        'voice_selection_mode': 'random',
        'voice_list': [
            {
                'voice_id': {
                    'service': 'ServiceA',
                    'voice_key': {'name': 'voice_2'}
                },
                'options': {
                },
                'weight': 1
            },
            {
                'voice_id': {
                    'service': 'ServiceA',
                    'voice_key': {'name': 'voice_3'}
                },
                'options': {
                },
                'weight': 1
            }            
        ]
    }
    assert voiceselection.serialize() == expected_output    

def test_voice_selection_random_to_single(qtbot):
    hypertts_instance = gui_testing_utils.get_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    # choose random mode
    # qtbot.mouseClick(voiceselection.radio_button_random, aqt.qt.Qt.MouseButton.LeftButton)
    voiceselection.radio_button_random.setChecked(True)

    # pick second voice and add it
    voiceselection.voices_combobox.setCurrentIndex(1) # pick second voice
    qtbot.mouseClick(voiceselection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)

    # pick third voice and add it
    voiceselection.voices_combobox.setCurrentIndex(2) # pick second voice
    qtbot.mouseClick(voiceselection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)    

    # check model change callback
    assert model_change_callback.model.selection_mode == constants.VoiceSelectionMode.random
    assert len(model_change_callback.model.get_voice_list()) == 2

    # go back to single
    voiceselection.radio_button_single.setChecked(True)
    # check model change callback
    assert model_change_callback.model.selection_mode == constants.VoiceSelectionMode.single

    # verify that the selected voices grid is empty
    assert voiceselection.voice_list_grid_layout.count() == 0


def test_voice_selection_random_remove_voices(qtbot):
    hypertts_instance = gui_testing_utils.get_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    # choose random mode
    # qtbot.mouseClick(voiceselection.radio_button_random, aqt.qt.Qt.MouseButton.LeftButton)
    voiceselection.radio_button_random.setChecked(True)

    # pick second voice and add it
    voiceselection.voices_combobox.setCurrentIndex(1) # pick second voice
    qtbot.mouseClick(voiceselection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)

    # pick third voice and add it
    voiceselection.voices_combobox.setCurrentIndex(2) # pick second voice
    qtbot.mouseClick(voiceselection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)    

    # check model change callback
    assert model_change_callback.model.selection_mode == constants.VoiceSelectionMode.random
    assert len(model_change_callback.model.get_voice_list()) == 2

    # now remove one of the voices
    logger.info('removing voice_row_1')
    remove_voice_button = dialog.findChild(aqt.qt.QPushButton, 'remove_voice_row_1')
    qtbot.mouseClick(remove_voice_button, aqt.qt.Qt.MouseButton.LeftButton)

    # check model change callback
    assert model_change_callback.model.selection_mode == constants.VoiceSelectionMode.random
    assert len(model_change_callback.model.get_voice_list()) == 1



def test_voice_selection_random_2(qtbot):
    hypertts_instance = gui_testing_utils.get_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    # choose random mode
    voiceselection.radio_button_random.setChecked(True)

    # add the first voice twice, but with different options
    testing_utils.voice_selection_voice_list_select('voice_a_1', 'ServiceA', voiceselection.voices_combobox)
    qtbot.mouseClick(voiceselection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)

    # change options
    speaking_rate_widget = dialog.findChild(aqt.qt.QDoubleSpinBox, "voice_option_speaking_rate")
    speaking_rate_widget.setValue(0.25)    

    # add again
    qtbot.mouseClick(voiceselection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)

    # build expected voice selection model
    expected_model = config_models.VoiceSelectionRandom()
    voice = [x for x in hypertts_instance.service_manager.full_voice_list() if x.service == 'ServiceA' and x.name == 'voice_a_1'][0]

    expected_model.add_voice(config_models.VoiceWithOptionsRandom(voice.voice_id, {}))
    expected_model.add_voice(config_models.VoiceWithOptionsRandom(voice.voice_id, {'speaking_rate': 0.25}))    

    assert voiceselection.voice_selection_model.serialize() == expected_model.serialize()


def test_voice_selection_priority_1(qtbot):
    hypertts_instance = gui_testing_utils.get_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    # choose random mode
    # qtbot.mouseClick(voiceselection.radio_button_random, aqt.qt.Qt.MouseButton.LeftButton)
    voiceselection.radio_button_priority.setChecked(True)

    # dialog.exec()

    # pick second voice and add it
    testing_utils.voice_selection_voice_list_select('voice_a_2', 'ServiceA', voiceselection.voices_combobox)
    qtbot.mouseClick(voiceselection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)

    # pick third voice and add it
    testing_utils.voice_selection_voice_list_select('voice_a_3', 'ServiceA', voiceselection.voices_combobox)
    qtbot.mouseClick(voiceselection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)    

    expected_model = config_models.VoiceSelectionPriority()
    voice_2 = [x for x in hypertts_instance.service_manager.full_voice_list() if x.service == 'ServiceA' and x.name == 'voice_a_2'][0]
    voice_3 = [x for x in hypertts_instance.service_manager.full_voice_list() if x.service == 'ServiceA' and x.name == 'voice_a_3'][0]

    expected_model.add_voice(config_models.VoiceWithOptionsPriority(voice_2.voice_id, {}))
    expected_model.add_voice(config_models.VoiceWithOptionsPriority(voice_3.voice_id, {}))

    assert voiceselection.voice_selection_model.serialize() == expected_model.serialize()

    # dialog.exec()


def test_voice_selection_filters(qtbot):
    manager = servicemanager.ServiceManager(testing_utils.get_test_services_dir(), f'{constants.DIR_HYPERTTS_ADDON}.test_services', True)
    manager.init_services()
    manager.get_service('ServiceA').enabled = True
    manager.get_service('ServiceB').enabled = True
    anki_utils = testing_utils.MockAnkiUtils({})

    hypertts_instance = hypertts.HyperTTS(anki_utils, manager)

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    # ensure filters are set to All by default
    assert voiceselection.audio_languages_combobox.currentText() == constants.LABEL_FILTER_ALL
    assert voiceselection.languages_combobox.currentText() == constants.LABEL_FILTER_ALL
    assert voiceselection.services_combobox.currentText() == constants.LABEL_FILTER_ALL
    assert voiceselection.genders_combobox.currentText() == constants.LABEL_FILTER_ALL

    # filter language to Japanese
    voiceselection.languages_combobox.setCurrentText('Japanese')

    # ensure japanese filter is enabled
    assert len(voiceselection.filtered_voice_list) < len(voiceselection.voice_list)
    assert len(voiceselection.filtered_voice_list) == voiceselection.voices_combobox.count()
    for voice in voiceselection.filtered_voice_list:
        assert languages.Language.ja in voice.languages

    # reset filters
    qtbot.mouseClick(voiceselection.reset_filters_button, aqt.qt.Qt.MouseButton.LeftButton)

    # ensure all voices are available now
    assert len(voiceselection.filtered_voice_list) == len(voiceselection.voice_list)

    # filter gender to male
    voiceselection.genders_combobox.setCurrentText('Male')

    # ensure only male voices appear
    assert len(voiceselection.filtered_voice_list) < len(voiceselection.voice_list)
    assert len(voiceselection.filtered_voice_list) == voiceselection.voices_combobox.count()
    for voice in voiceselection.filtered_voice_list:
        assert voice.gender == constants.Gender.Male

    # reset filters again
    qtbot.mouseClick(voiceselection.reset_filters_button, aqt.qt.Qt.MouseButton.LeftButton)
    # ensure all voices are available now
    assert len(voiceselection.filtered_voice_list) == len(voiceselection.voice_list)
    
    # filter with two different conditions
    voiceselection.languages_combobox.setCurrentText('Japanese')
    voiceselection.genders_combobox.setCurrentText('Female')

    # ensure only female japanese voices are present
    assert len(voiceselection.filtered_voice_list) < len(voiceselection.voice_list)
    assert len(voiceselection.filtered_voice_list) == voiceselection.voices_combobox.count()
    for voice in voiceselection.filtered_voice_list:
        assert voice.gender == constants.Gender.Female
        assert languages.Language.ja in voice.languages

    # reset filters again
    qtbot.mouseClick(voiceselection.reset_filters_button, aqt.qt.Qt.MouseButton.LeftButton)    

    # filter by audio language
    # ========================
    voiceselection.audio_languages_combobox.setCurrentText('French (France)')
    # ensure only french voices are present
    assert len(voiceselection.filtered_voice_list) < len(voiceselection.voice_list)
    assert len(voiceselection.filtered_voice_list) == voiceselection.voices_combobox.count()
    for voice in voiceselection.filtered_voice_list:
        assert languages.AudioLanguage.fr_FR in voice.audio_languages

    # reset filters again
    qtbot.mouseClick(voiceselection.reset_filters_button, aqt.qt.Qt.MouseButton.LeftButton)    


    # filter by service
    # =================
    voiceselection.services_combobox.setCurrentText('ServiceA')
    # ensure only ServiceA voices are present
    assert len(voiceselection.filtered_voice_list) < len(voiceselection.voice_list)
    assert len(voiceselection.filtered_voice_list) == voiceselection.voices_combobox.count()
    for voice in voiceselection.filtered_voice_list:
        assert voice.service == 'ServiceA'

    # dialog.exec()

def test_voice_selection_samples(qtbot):
    hypertts_instance = gui_testing_utils.get_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    testing_utils.voice_selection_voice_list_select('voice_a_1', 'ServiceA', voiceselection.voices_combobox)
    # voiceselection.voices_combobox.setCurrentIndex(1)

    # simulate selection from the preview grid
    voiceselection.sample_text_selected('Bonjour')

    qtbot.mouseClick(voiceselection.play_sample_button, aqt.qt.Qt.MouseButton.LeftButton)

    assert hypertts_instance.anki_utils.played_sound == {
        'source_text': 'Bonjour',
        'voice': {
            'gender': 'Male', 
            'audio_languages': ['fr_FR'],
            'name': 'voice_a_1', 
            'service': 'ServiceA',
            'voice_key': {'name': 'voice_1'},
            'service_fee': 'free',
        },
        'options': {}
    }

    # dialog.exec()

def test_voice_selection_load_model(qtbot):
    hypertts_instance = gui_testing_utils.get_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_2 = [x for x in voice_list if x.name == 'voice_a_2'][0]
    voice_a_3 = [x for x in voice_list if x.name == 'voice_a_3'][0]

    # single voice
    # ============

    model = config_models.VoiceSelectionSingle()
    model.voice = config_models.VoiceWithOptions(voice_a_2.voice_id, {'speaking_rate': 3.5})

    voiceselection.load_model(model)

    assert voiceselection.radio_button_single.isChecked()
    assert voiceselection.voices_combobox.currentText() == str(voice_a_2)


    speaking_rate_widget = voiceselection.voice_options_widgets['voice_option_speaking_rate']
    assert speaking_rate_widget != None
    assert speaking_rate_widget.value() == 3.5

    # single voice, ogg format
    # ========================

    model = config_models.VoiceSelectionSingle()
    model.voice = config_models.VoiceWithOptions(voice_a_2.voice_id, {'format': 'ogg_opus'})

    voiceselection.load_model(model)

    assert voiceselection.radio_button_single.isChecked()
    assert voiceselection.voices_combobox.currentText() == str(voice_a_2)


    format_widget = voiceselection.voice_options_widgets['voice_option_format']
    assert format_widget != None
    assert format_widget.currentText() == 'ogg_opus'

    # single voice, mp3 format
    # ========================

    model = config_models.VoiceSelectionSingle()
    model.voice = config_models.VoiceWithOptions(voice_a_2.voice_id, {'format': 'mp3'})

    voiceselection.load_model(model)

    assert voiceselection.radio_button_single.isChecked()
    assert voiceselection.voices_combobox.currentText() == str(voice_a_2)


    format_widget = voiceselection.voice_options_widgets['voice_option_format']
    assert format_widget != None
    assert format_widget.currentText() == 'mp3'

    # random
    # =======

    model = config_models.VoiceSelectionRandom()
    model.add_voice(config_models.VoiceWithOptionsRandom(voice_a_2.voice_id, {'speaking_rate': 2.5}))
    model.add_voice(config_models.VoiceWithOptionsRandom(voice_a_3.voice_id, {}))

    voiceselection.load_model(model)
    
    assert voiceselection.radio_button_random.isChecked()

    assert voiceselection.voice_list_grid_layout.itemAt(0).widget().text() == str(voice_a_2) + ' (speaking_rate: 2.5)'
    assert voiceselection.voice_list_grid_layout.itemAt(3).widget().text() == str(voice_a_3)

    # priority
    # ========

    model = config_models.VoiceSelectionPriority()
    model.add_voice(config_models.VoiceWithOptionsPriority(voice_a_2.voice_id, {'speaking_rate': 2.5}))
    model.add_voice(config_models.VoiceWithOptionsPriority(voice_a_3.voice_id, {}))

    voiceselection.load_model(model)
    
    assert voiceselection.radio_button_priority.isChecked()

    assert voiceselection.voice_list_grid_layout.itemAt(0).widget().text() == str(voice_a_2) + ' (speaking_rate: 2.5)'
    assert voiceselection.voice_list_grid_layout.itemAt(4).widget().text() == str(voice_a_3)    

    # dialog.exec()





def test_batch_source_1(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')    

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    field_list = hypertts_instance.get_all_fields_from_notes(note_id_list)
    batch_source = component_source.BatchSource(hypertts_instance, field_list, model_change_callback.model_updated)
    dialog.addChildWidget(batch_source.draw())

    # the field selected should be "Chinese"
    expected_source_model = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='Chinese')

    # the simple stack item should be selected
    assert batch_source.source_config_stack.currentIndex() == batch_source.SOURCE_CONFIG_STACK_SIMPLE

    assert batch_source.batch_source_model == expected_source_model

    # select another field, 'English'
    batch_source.source_field_combobox.setCurrentText('English')
    expected_source_model.source_field = 'English'

    assert batch_source.batch_source_model == expected_source_model
    
    # enable "use selection"
    batch_source.use_selection_checkbox.setChecked(True)
    expected_source_model.use_selection = True
    assert batch_source.batch_source_model == expected_source_model

    # disable "use selection"
    batch_source.use_selection_checkbox.setChecked(False)
    expected_source_model.use_selection = False
    assert batch_source.batch_source_model == expected_source_model

    # select template mode
    batch_source.batch_mode_combobox.setCurrentText('template')
    assert batch_source.source_config_stack.currentIndex() == batch_source.SOURCE_CONFIG_STACK_TEMPLATE

    # enter template format
    qtbot.keyClicks(batch_source.simple_template_input, '{Chinese}')

    expected_source_model = config_models.BatchSource(mode=constants.BatchMode.template, 
        source_template='{Chinese}')

    assert batch_source.batch_source_model == expected_source_model

    # load model tests
    # ================
    # the field selected should be "English"
    model = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='English')

    batch_source.load_model(model)

    assert batch_source.batch_mode_combobox.currentText() == 'simple'
    assert batch_source.source_field_combobox.currentText() == 'English'

    model.source_field = 'Chinese'

    batch_source.load_model(model)

    assert batch_source.batch_mode_combobox.currentText() == 'simple'
    assert batch_source.source_field_combobox.currentText() == 'Chinese'

    model.mode = constants.BatchMode.template
    model.source_template = '{English}'
    model.template_format_version = constants.TemplateFormatVersion.v1

    batch_source.load_model(model)

    assert batch_source.batch_mode_combobox.currentText() == 'template'
    assert batch_source.simple_template_input.text() == '{English}'
    assert batch_source.use_selection_checkbox.isChecked() == False

    # load simple model, but with use_selection = True
    # =================================================
    model = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='English', use_selection=True)
    batch_source.load_model(model)

    assert batch_source.batch_mode_combobox.currentText() == 'simple'
    assert batch_source.source_field_combobox.currentText() == 'English'
    assert batch_source.use_selection_checkbox.isChecked() == True    

    # load advanced template
    model.mode = constants.BatchMode.advanced_template
    model.source_template = f"""result = 'yoyo'"""
    model.template_format_version = constants.TemplateFormatVersion.v1

    logger.debug('clearing model change callback object')
    model_change_callback.clear_model()
    logger.debug('loading advanced model')
    batch_source.load_model(model)
    logger.debug('done loading advanced model')

    assert batch_source.advanced_template_input.toPlainText() == f"""result = 'yoyo'"""

    # dialog.exec()

def test_target_base(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')    

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    field_list = hypertts_instance.get_all_fields_from_notes(note_id_list)
    batch_target = component_target.BatchTarget(hypertts_instance, field_list, model_change_callback.model_updated)
    dialog.addChildWidget(batch_target.draw())

    # pick the Sound field
    batch_target.target_field_combobox.setCurrentText('Sound')

    assert batch_target.batch_target_model.target_field == 'Sound'
    assert batch_target.batch_target_model.text_and_sound_tag == False
    assert batch_target.batch_target_model.remove_sound_tag == True

    # change some options
    batch_target.radio_button_text_sound.setChecked(True)
    assert batch_target.batch_target_model.text_and_sound_tag == True

    batch_target.radio_button_keep_sound.setChecked(True)
    assert batch_target.batch_target_model.remove_sound_tag == False

    # load model tests
    # ================

    target_field = 'Chinese'
    text_and_sound_tag = False
    remove_sound_tag = True
    model = config_models.BatchTarget(target_field, text_and_sound_tag, remove_sound_tag)
    batch_target.load_model(model)

    assert batch_target.target_field_combobox.currentText() == 'Chinese'
    assert batch_target.radio_button_sound_only.isChecked() == True
    assert batch_target.radio_button_text_sound.isChecked() == False

    assert batch_target.radio_button_keep_sound.isChecked() == False
    assert batch_target.radio_button_remove_sound.isChecked() == True

    target_field = 'Pinyin'
    text_and_sound_tag = True
    remove_sound_tag = True
    model = config_models.BatchTarget(target_field, text_and_sound_tag, remove_sound_tag)
    batch_target.load_model(model)

    assert batch_target.target_field_combobox.currentText() == 'Pinyin'

    assert batch_target.radio_button_sound_only.isChecked() == False
    assert batch_target.radio_button_text_sound.isChecked() == True

    assert batch_target.radio_button_keep_sound.isChecked() == False
    assert batch_target.radio_button_remove_sound.isChecked() == True

    target_field = 'Sound'
    text_and_sound_tag = True
    remove_sound_tag = False
    model = config_models.BatchTarget(target_field, text_and_sound_tag, remove_sound_tag)
    batch_target.load_model(model)

    assert batch_target.target_field_combobox.currentText() == 'Sound'
    assert batch_target.radio_button_sound_only.isChecked() == False
    assert batch_target.radio_button_text_sound.isChecked() == True

    assert batch_target.radio_button_keep_sound.isChecked() == True
    assert batch_target.radio_button_remove_sound.isChecked() == False

    target_field = 'Chinese'
    text_and_sound_tag = False
    remove_sound_tag = False
    model = config_models.BatchTarget(target_field, text_and_sound_tag, remove_sound_tag)
    batch_target.load_model(model)

    assert batch_target.target_field_combobox.currentText() == 'Chinese'
    assert batch_target.radio_button_sound_only.isChecked() == True
    assert batch_target.radio_button_text_sound.isChecked() == False

    assert batch_target.radio_button_keep_sound.isChecked() == True
    assert batch_target.radio_button_remove_sound.isChecked() == False

def fixtures_source_easy(build_editor_context_fn):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')    

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # create editor context
    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    editor_context = build_editor_context_fn(note_1)

    # instantiate component
    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    source = component_easy_source.ComponentEasySource(hypertts_instance, editor_context, model_change_callback.model_updated)
    dialog.addChildWidget(source.draw())

    return dialog, source, model_change_callback

def test_component_easy_source_initial_field_text_no_current_field(qtbot):
    def build_editor_context_fn(note):
        # the user has not put the cursor in a field
        return config_models.EditorContext(
            note=note, 
            editor=None, 
            add_mode=False, 
            selected_text=None, 
            current_field=None, 
            clipboard=None)
    dialog, source, model_change_callback = fixtures_source_easy(build_editor_context_fn)

    # verify initial state
    assert source.source_text_origin == config_models.SourceTextOrigin.FIELD_TEXT
    assert source.get_current_text() == '老人家'
    assert source.field_radio.isEnabled() == True
    # field radio should be selected
    assert source.field_radio.isChecked() == True
    # should have gotten a model callback 
    # the field selected should be "Chinese"
    expected_source_model = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='Chinese')
    assert source.batch_source_model == expected_source_model
    assert model_change_callback.model == expected_source_model



def test_component_easy_source_initial_field_text_current_field_1(qtbot):
    def build_editor_context_fn(note):
        return config_models.EditorContext(
            note=note, 
            editor=None, 
            add_mode=False, 
            selected_text=None, 
            current_field='Chinese', 
            clipboard=None)
    dialog, source, model_change_callback = fixtures_source_easy(build_editor_context_fn)

    # verify initial state
    assert source.source_text_origin == config_models.SourceTextOrigin.FIELD_TEXT
    assert source.get_current_text() == '老人家'
    assert source.field_radio.isEnabled() == True
    # field radio should be selected
    assert source.field_radio.isChecked() == True
    # field combobox should be enabled
    assert source.field_combobox.isEnabled() == True

    # we have no selected text, selection_radio should be disabled
    assert source.selection_radio.isEnabled() == False
    assert source.selection_preview_label.isEnabled() == False
    assert source.selection_preview_label.text() == constants.GUI_TEXT_EASY_SOURCE_SELECTION_NO_TEXT

    # we have no clipboard text, clipboard_radio should be disabled
    assert source.clipboard_radio.isEnabled() == False
    assert source.clipboard_preview_label.isEnabled() == False
    assert source.clipboard_preview_label.text() == constants.GUI_TEXT_EASY_SOURCE_CLIPBOARD_NO_TEXT

    # modify text
    source.source_text_edit.setPlainText('你好')
    assert source.get_current_text() == '你好'

def test_component_easy_source_initial_field_text_current_field_2(qtbot):
    def build_editor_context_fn(note):
        return config_models.EditorContext(
            note=note, 
            editor=None, 
            add_mode=False, 
            selected_text=None, 
            current_field='English',  # user has placed the cursor in the english field
            clipboard=None)
    dialog, source, model_change_callback = fixtures_source_easy(build_editor_context_fn)

    # verify initial state
    assert source.source_text_origin == config_models.SourceTextOrigin.FIELD_TEXT
    assert source.get_current_text() == 'old people'
    assert source.field_radio.isEnabled() == True
    # field radio should be selected
    assert source.field_radio.isChecked() == True
    # field combobox should be enabled
    assert source.field_combobox.isEnabled() == True

    # check model
    # the field selected should be "English"
    expected_source_model = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='English')
    assert source.batch_source_model == expected_source_model
    assert model_change_callback.model == expected_source_model    

def test_component_easy_source_initial_clipboard(qtbot):
    def build_editor_context_fn(note):
        return config_models.EditorContext(
            note=note, 
            editor=None, 
            add_mode=False, 
            selected_text=None, 
            current_field='Chinese', 
            clipboard='override text')
    dialog, source, model_change_callback = fixtures_source_easy(build_editor_context_fn)

    # verify initial state
    assert source.source_text_origin == config_models.SourceTextOrigin.CLIPBOARD
    assert source.get_current_text() == 'override text'
    
    # source field is always enabled
    assert source.field_radio.isEnabled() == True
    # but not checked (since we have clipboard text)
    assert source.field_radio.isChecked() == False
    assert source.field_combobox.isEnabled() == False

    # we have no selected text, selection_radio should be disabled
    assert source.selection_radio.isEnabled() == False
    assert source.selection_preview_label.isEnabled() == False

    # we have clipboard text, so this should be the default option
    assert source.clipboard_radio.isEnabled() == True
    assert source.clipboard_radio.isChecked() == True
    assert source.clipboard_preview_label.isEnabled() == True
    assert source.clipboard_preview_label.text() == '(override text)'

    # the field selected should be "Chinese", just because it's the first field
    expected_source_model = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='Chinese')
    assert source.batch_source_model == expected_source_model
    assert model_change_callback.model == expected_source_model    

def test_component_easy_source_initial_clipboard_selected(qtbot):
    def build_editor_context_fn(note):
        return config_models.EditorContext(
            note=note, 
            editor=None, 
            add_mode=False, 
            selected_text='selected text',
            current_field='Chinese', 
            clipboard='clipboard text')
    dialog, source, model_change_callback = fixtures_source_easy(build_editor_context_fn)

    # verify initial state
    assert source.source_text_origin == config_models.SourceTextOrigin.CLIPBOARD
    assert source.get_current_text() == 'clipboard text'
    
    # source field is always enabled
    assert source.field_radio.isEnabled() == True
    # but not checked (since we have clipboard text)
    assert source.field_radio.isChecked() == False

    # we have no selected text, selection_radio should be disabled
    assert source.selection_radio.isEnabled() == True
    assert source.selection_radio.isChecked() == False
    assert source.selection_preview_label.isEnabled() == True
    assert source.selection_preview_label.text() == '(selected text)'

    # we have clipboard text, so this should be the default option
    assert source.clipboard_radio.isEnabled() == True
    assert source.clipboard_radio.isChecked() == True    
    assert source.clipboard_preview_label.isEnabled() == True
    assert source.clipboard_preview_label.text() == '(clipboard text)'

def fixtures_target_easy():
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')    

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    field_list = hypertts_instance.get_all_fields_from_notes(note_id_list)

    source_field = 'Chinese'
    other_field_list = field_list
    other_field_list.remove(source_field)


    batch_target = component_target_easy.BatchTargetEasy(hypertts_instance, source_field, other_field_list, model_change_callback.model_updated)
    dialog.addChildWidget(batch_target.draw())

    return dialog, batch_target, model_change_callback

def test_target_easy_defaults(qtbot):
    dialog, batch_target, model_change_callback = fixtures_target_easy()

    # check defaults
    # ==============

    assert batch_target.radio_button_same_field.isChecked() == True
    assert batch_target.radio_button_after.isChecked() == True
    assert batch_target.radio_button_text_sound.isChecked() == True
    assert batch_target.radio_button_remove_sound.isChecked() == True

    # check visibility
    assert batch_target.sound_options_widget.isVisibleTo(dialog) == False
    assert batch_target.target_field_widget.isVisibleTo(dialog) == False
    assert batch_target.insert_location_widget.isVisibleTo(dialog) == True
    
    # check initial model update
    assert model_change_callback.model.same_field == True
    assert model_change_callback.model.insert_location == config_models.InsertLocation.AFTER
    assert model_change_callback.model.text_and_sound_tag == True
    assert model_change_callback.model.remove_sound_tag == True

def test_target_easy_model_updates(qtbot):
    dialog, batch_target, model_change_callback = fixtures_target_easy()

    # set same_field to false
    batch_target.radio_button_different_field.setChecked(True)
    assert model_change_callback.model.same_field == False
    batch_target.radio_button_same_field.setChecked(True)
    assert model_change_callback.model.same_field == True

    batch_target.radio_button_cursor.setChecked(True)
    assert model_change_callback.model.insert_location == config_models.InsertLocation.CURSOR_LOCATION

    batch_target.radio_button_after.setChecked(True)
    assert model_change_callback.model.insert_location == config_models.InsertLocation.AFTER

    # text and sound 
    batch_target.radio_button_sound_only.setChecked(True)
    assert model_change_callback.model.text_and_sound_tag == False
    batch_target.radio_button_text_sound.setChecked(True)
    assert model_change_callback.model.text_and_sound_tag == True

    # remove sound tag
    batch_target.radio_button_keep_sound.setChecked(True)
    assert model_change_callback.model.remove_sound_tag == False
    batch_target.radio_button_remove_sound.setChecked(True)
    assert model_change_callback.model.remove_sound_tag == True

def test_target_easy_model_load(qtbot):
    dialog, batch_target, model_change_callback = fixtures_target_easy()

    # config 1 
    # ========

    model = config_models.BatchTarget(
        target_field = 'Sound',
        text_and_sound_tag = False,
        remove_sound_tag = True,
        insert_location = config_models.InsertLocation.AFTER,
        same_field = False
    )

    batch_target.load_model(model)

    # assert gui controls state
    assert batch_target.radio_button_same_field.isChecked() == False
    assert batch_target.radio_button_different_field.isChecked() == True
    assert batch_target.target_field_combobox.currentText() == 'Sound'
    assert batch_target.radio_button_sound_only.isChecked() == True

    # config 2
    # ========

    model = config_models.BatchTarget(
        target_field = 'Sound',
        text_and_sound_tag = True,
        remove_sound_tag = False,
        insert_location = config_models.InsertLocation.AFTER,
        same_field = False
    )

    batch_target.load_model(model)

    # assert gui controls state
    assert batch_target.radio_button_same_field.isChecked() == False
    assert batch_target.radio_button_different_field.isChecked() == True
    assert batch_target.target_field_combobox.currentText() == 'Sound'
    assert batch_target.radio_button_text_sound.isChecked() == True
    assert batch_target.radio_button_keep_sound.isChecked() == True

    # config 3
    # ========

    model = config_models.BatchTarget(
        target_field = None,
        text_and_sound_tag = True,
        remove_sound_tag = False,
        insert_location = config_models.InsertLocation.CURSOR_LOCATION,
        same_field = True
    )

    batch_target.load_model(model)

    # assert gui controls state
    assert batch_target.radio_button_same_field.isChecked() == True
    assert batch_target.radio_button_different_field.isChecked() == False
    assert batch_target.radio_button_cursor.isChecked() == True
    assert batch_target.target_field_widget.isVisibleTo(dialog) == False
    assert batch_target.sound_options_widget.isVisibleTo(dialog) == False
    assert batch_target.insert_location_widget.isVisibleTo(dialog) == True

    # config 4
    # ========

    model = config_models.BatchTarget(
        target_field = None,
        text_and_sound_tag = True,
        remove_sound_tag = False,
        insert_location = config_models.InsertLocation.AFTER,
        same_field = True
    )

    batch_target.load_model(model)

    # assert gui controls state
    assert batch_target.radio_button_same_field.isChecked() == True
    assert batch_target.radio_button_different_field.isChecked() == False
    assert batch_target.radio_button_after.isChecked() == True
    assert batch_target.target_field_widget.isVisibleTo(dialog) == False
    assert batch_target.sound_options_widget.isVisibleTo(dialog) == False
    assert batch_target.insert_location_widget.isVisibleTo(dialog) == True



def test_batch_preview(qtbot):

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    # configure delay on service A
    # hypertts_instance.service_manager.get_service('ServiceA').configure({'delay': 1.0})

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    

    voice_list = hypertts_instance.service_manager.full_voice_list()

    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    voice_selection = config_models.VoiceSelectionSingle()
    voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1.voice_id, {}))

    batch_config = config_models.BatchConfig(hypertts_instance.anki_utils)
    source = config_models.BatchSource(mode=constants.BatchMode.simple, source_field='Chinese')
    target = config_models.BatchTarget('Sound', False, True)

    batch_config.set_source(source)
    batch_config.set_target(target)
    batch_config.set_voice_selection(voice_selection)    

    batch_preview_callback = gui_testing_utils.MockBatchPreviewCallback()
    batch_preview = component_batch_preview.BatchPreview(hypertts_instance, dialog, note_id_list, 
        batch_preview_callback.sample_selected,
        batch_preview_callback.batch_start,
        batch_preview_callback.batch_end)
    batch_preview.load_model(batch_config)
    dialog.addChildLayout(batch_preview.draw())

    # dialog.exec()
    # return 


def test_batch_dialog_1(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    

    # test saving of config
    # =====================

    def dialog_input_sequence(dialog):
        # select a source field and target field
        dialog.batch_component.source.source_field_combobox.setCurrentText('English')
        dialog.batch_component.target.target_field_combobox.setCurrentText('Sound')

        # set profile name
        # click rename button
        preset_name = 'my preset 2'
        hypertts_instance.anki_utils.ask_user_get_text_response = preset_name
        qtbot.mouseClick(dialog.batch_component.profile_rename_button, aqt.qt.Qt.MouseButton.LeftButton)
        # batch.profile_name_combobox.setCurrentText('batch profile 1')

        # save button should be enabled
        assert dialog.batch_component.profile_save_button.isEnabled() == True
        # save
        qtbot.mouseClick(dialog.batch_component.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)
        # should be disabled after saving
        assert dialog.batch_component.profile_save_button.isEnabled() == False
        assert dialog.batch_component.profile_save_button.text() == 'Save'

        print(hypertts_instance.anki_utils.written_config)
        expected_uuid = 'uuid_1'
        assert expected_uuid in hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS]

        # try to deserialize that config, it should have the English field selected
        deserialized_model = hypertts_instance.load_preset(expected_uuid)
        assert deserialized_model.name == preset_name
        assert deserialized_model.source.source_field == 'English'
        assert deserialized_model.target.target_field == 'Sound'

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    component_batch.create_component_batch_browser_new_preset(hypertts_instance, note_id_list, 'my preset 1')

    # test loading of config
    # ======================

    def dialog_input_sequence(dialog):
        # we should be able to open a profile
        assert dialog.batch_component.profile_open_button.isEnabled() == True
        hypertts_instance.anki_utils.ask_user_choose_from_list_response_string = 'my preset 2'
        # click the open profile button
        qtbot.mouseClick(dialog.batch_component.profile_open_button, aqt.qt.Qt.MouseButton.LeftButton)
        # now, the preset should be loaded
        # save button should be disabled, we didn't make any changes
        assert dialog.batch_component.profile_save_button.isEnabled() == False

        # assertions on GUI
        assert dialog.batch_component.source.source_field_combobox.currentText() == 'English'
        assert dialog.batch_component.target.target_field_combobox.currentText() == 'Sound'
        assert dialog.batch_component.profile_name_label.text() == 'my preset 2'
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    component_batch.create_component_batch_browser_new_preset(hypertts_instance, note_id_list, 'my preset 1')        
    
    # dialog.exec()

    # test loading with empty preset, then duplicating
    # ================================================

    def dialog_input_sequence(dialog):
        # we just created a new profile, source field is not english
        assert dialog.batch_component.source.source_field_combobox.currentText() != 'English'

        # wo we'll duplicate the profile 'my preset 2'
        assert dialog.batch_component.profile_duplicate_button.isEnabled() == True
        hypertts_instance.anki_utils.ask_user_choose_from_list_response_string = 'my preset 2'

        # reset the uuid counter to be more predictable
        hypertts_instance.anki_utils.uuid_current_num = 10
        expected_uuid = f'uuid_{hypertts_instance.anki_utils.uuid_current_num + 1}'
        # press the duplicate button
        qtbot.mouseClick(dialog.batch_component.profile_duplicate_button, aqt.qt.Qt.MouseButton.LeftButton)

        # profile name should have changed
        assert dialog.batch_component.profile_name_label.text() == 'my preset 2 (copy)'
        # the source field should be english, just like for 'my preset 2'
        assert dialog.batch_component.source.source_field_combobox.currentText() == 'English'

        # assert save button is enabled
        assert dialog.batch_component.profile_save_button.isEnabled() == True
        # save the preset
        qtbot.mouseClick(dialog.batch_component.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)

        # make sure the preset was saved
        pprint.pprint(hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS])
        assert expected_uuid in hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS]
        # ensure the name of the preset that was saved is correct
        assert hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS][expected_uuid]['name'] == 'my preset 2 (copy)'

        # rename the preset, and save it 
        hypertts_instance.anki_utils.ask_user_get_text_response = 'my preset 3'
        qtbot.mouseClick(dialog.batch_component.profile_rename_button, aqt.qt.Qt.MouseButton.LeftButton)
        # save
        qtbot.mouseClick(dialog.batch_component.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)
        # make sure the name is correct
        assert hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS][expected_uuid]['name'] == 'my preset 3'

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    component_batch.create_component_batch_browser_new_preset(hypertts_instance, note_id_list, 'my preset 1')

    # test launching with a particular preset
    # =======================================

    def dialog_input_sequence(dialog):

        # assertions on GUI
        assert dialog.batch_component.source.source_field_combobox.currentText() == 'English'
        assert dialog.batch_component.target.target_field_combobox.currentText() == 'Sound'

        # dialog.exec()

        assert dialog.batch_component.profile_save_button.isEnabled() == False    

        # the "apply to notes" button should be focused
        assert dialog.focusWidget() == dialog.batch_component.apply_button, "Apply to Notes button should be focused"

        # play sound preview
        # ==================

        # select second row
        index_second_row = dialog.batch_component.preview.batch_preview_table_model.createIndex(1, 0)
        dialog.batch_component.preview.table_view.selectionModel().select(index_second_row, aqt.qt.QItemSelectionModel.SelectionFlag.Select)
        # select voice
        testing_utils.voice_selection_voice_list_select('voice_a_1', 'ServiceA', dialog.batch_component.voice_selection.voices_combobox)
        # press preview button
        qtbot.mouseClick(dialog.batch_component.preview_sound_button, aqt.qt.Qt.MouseButton.LeftButton)
        # dialog.exec()

        assert hypertts_instance.anki_utils.played_sound == {
            'source_text': 'hello',
            'voice': {
                'gender': 'Male', 
                'audio_languages': ['fr_FR'],
                'service_fee': 'free',
                'name': 'voice_a_1', 
                'service': 'ServiceA',
                'voice_key': {'name': 'voice_1'}
            },
            'options': {}
        }    

        # load audio
        # ==========

        dialog.batch_component.source.source_field_combobox.setCurrentText('Chinese')
        qtbot.mouseClick(dialog.batch_component.apply_button, aqt.qt.Qt.MouseButton.LeftButton)

        # make sure notes were updated
        note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
        assert 'Sound' in note_1.set_values 

        sound_tag = note_1.set_values['Sound']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

        assert audio_data['source_text'] == '老人家'

        note_2 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_2)
        assert 'Sound' in note_2.set_values 

        sound_tag = note_2.set_values['Sound']
        audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
        audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

        assert audio_data['source_text'] == '你好'

        # button state
        assert dialog.batch_component.apply_button.isEnabled() == False
        assert dialog.batch_component.cancel_button.isEnabled() == True
        assert dialog.batch_component.cancel_button.text() == 'Close'

        # delete profile
        # ==============


        assert dialog.batch_component.profile_name_label.text() == 'my preset 2'
        assert dialog.batch_component.profile_delete_button.isEnabled() == True
        qtbot.mouseClick(dialog.batch_component.profile_delete_button, aqt.qt.Qt.MouseButton.LeftButton)

        # make sure the profile was deleted
        assert 'uuid_1' not in hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS]

        # we should have a new preset
        assert dialog.batch_component.profile_name_label.text() == 'Preset 1'
    
    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    component_batch.create_component_batch_browser_existing_preset(hypertts_instance, note_id_list, 'uuid_1')


def test_batch_dialog_new_preset_save_enabled(qtbot):
    # create a preset
    # save it
    # delete it
    # new preset gets created
    # the save button should be enabled

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    

    # test saving of config
    # =====================

    def dialog_input_sequence(dialog):
        # save button should be enabled
        assert dialog.batch_component.profile_save_button.isEnabled() == True
        # delete button should be disabled, profile was never saved
        assert dialog.batch_component.profile_delete_button.isEnabled() == False

        # save the preset
        qtbot.mouseClick(dialog.batch_component.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)
        # save button should now be disabled
        assert dialog.batch_component.profile_save_button.isEnabled() == False
        # delete button should now be enabled
        assert dialog.batch_component.profile_delete_button.isEnabled() == True

        # delete the preset
        qtbot.mouseClick(dialog.batch_component.profile_delete_button, aqt.qt.Qt.MouseButton.LeftButton)

        # we should be on a new preset
        assert dialog.batch_component.profile_name_label.text() == 'Preset 1'
        # save button should be enabled
        assert dialog.batch_component.profile_save_button.isEnabled() == True
        # delete button should be enabled, because we have a new profile

        # now save the profile, it should work
        qtbot.mouseClick(dialog.batch_component.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)
        assert 'uuid_2' in hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS]

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    component_batch.create_component_batch_browser_new_preset(hypertts_instance, note_id_list, 'my preset 5')


def test_batch_dialog_sound_preview_error(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    

    # test saving of config
    # =====================

    def dialog_input_sequence(dialog):

        # select English source
        dialog.batch_component.source.source_field_combobox.setCurrentText('English')
        
        # play sound preview with error voice
        # ===================================
        # dialog.exec()

        # select error voice
        testing_utils.voice_selection_voice_list_select('notfound', 'ServiceB', dialog.batch_component.voice_selection.voices_combobox)

        # select second row
        index_second_row = dialog.batch_component.preview.batch_preview_table_model.createIndex(1, 0)
        dialog.batch_component.preview.table_view.selectionModel().select(index_second_row, aqt.qt.QItemSelectionModel.SelectionFlag.Select)

        # dialog.exec()

        # press preview button
        qtbot.mouseClick(dialog.batch_component.preview_sound_button, aqt.qt.Qt.MouseButton.LeftButton)

        assert str(hypertts_instance.anki_utils.last_exception) == 'Audio not found for [hello] (voice: Japanese, Male, notfound (ServiceB))'

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    component_batch.create_component_batch_browser_new_preset(hypertts_instance, note_id_list, 'my preset 1')        

def test_batch_dialog_voice_selection_sample(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    

    def dialog_input_sequence(dialog):
        # select English source
        dialog.batch_component.source.source_field_combobox.setCurrentText('English')

        # play sample button should be disabled
        assert dialog.batch_component.voice_selection.play_sample_button.isEnabled() == False

        # select voice
        testing_utils.voice_selection_voice_list_select('voice_a_2', 'ServiceA', dialog.batch_component.voice_selection.voices_combobox)

        # now select the first row
        index_first_row = dialog.batch_component.preview.batch_preview_table_model.createIndex(0, 0)
        dialog.batch_component.preview.table_view.selectionModel().select(index_first_row, aqt.qt.QItemSelectionModel.SelectionFlag.Select)    

        # button should be enabled
        assert dialog.batch_component.voice_selection.play_sample_button.isEnabled() == True

        # press button
        qtbot.mouseClick(dialog.batch_component.voice_selection.play_sample_button, aqt.qt.Qt.MouseButton.LeftButton)

        assert hypertts_instance.anki_utils.played_sound == {
            'source_text': 'old people',
            'voice': {
                'gender': 'Female', 
                'audio_languages': ['en_US'],
                'name': 'voice_a_2', 
                'service': 'ServiceA',
                'voice_key': {'name': 'voice_2'},
                'service_fee': 'free',
            },
            'options': {}
        }    

        # now change to Chinese field
        dialog.batch_component.source.source_field_combobox.setCurrentText('Chinese')

        # press play sample button again
        qtbot.mouseClick(dialog.batch_component.voice_selection.play_sample_button, aqt.qt.Qt.MouseButton.LeftButton)
        assert hypertts_instance.anki_utils.played_sound == {
            'source_text': '老人家',
            'voice': {
                'gender': 'Female', 
                'audio_languages': ['en_US'],
                'name': 'voice_a_2', 
                'service': 'ServiceA',
                'voice_key': {'name': 'voice_2'},
                'service_fee': 'free',
            },
            'options': {}
        }        

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    component_batch.create_component_batch_browser_new_preset(hypertts_instance, note_id_list, 'my preset 1')


    # dialog.exec()

def test_batch_dialog_load_missing_field(qtbot):
    logger.info('test_batch_dialog_load_missing_field')
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    

    # test saving of config
    # =====================

    def dialog_input_sequence(dialog):

        # select a source field and target field
        # target field will be Chinese
        dialog.batch_component.source.source_field_combobox.setCurrentText('English')
        dialog.batch_component.target.target_field_combobox.setCurrentText('Chinese')

        # rename profile
        hypertts_instance.anki_utils.ask_user_get_text_response = 'batch profile 1'
        qtbot.mouseClick(dialog.batch_component.profile_rename_button, aqt.qt.Qt.MouseButton.LeftButton)

        # click save button
        qtbot.mouseClick(dialog.batch_component.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    component_batch.create_component_batch_browser_new_preset(hypertts_instance, note_id_list, 'my preset 1')

    # test loading of config
    # ======================
    # use the german note type, which doesn't have the Chinese field
    note_id_list = [config_gen.note_id_german_1]

    def dialog_input_sequence(dialog):

        # open "batch profile 1"
        assert dialog.batch_component.profile_open_button.isEnabled() == True
        hypertts_instance.anki_utils.ask_user_choose_from_list_response_string = 'batch profile 1'
        # click the open profile button
        qtbot.mouseClick(dialog.batch_component.profile_open_button, aqt.qt.Qt.MouseButton.LeftButton)

        # check the target field on the model
        # ===================================

        target_field_selected = dialog.batch_component.target.target_field_combobox.currentText()
        assert dialog.batch_component.get_model().target.target_field == target_field_selected

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    component_batch.create_component_batch_browser_new_preset(hypertts_instance, note_id_list, 'my preset 1')



def test_batch_dialog_browser_manual(qtbot):
    # HYPERTTS_BATCH_DIALOG_DEBUG=yes pytest test_components.py -k test_batch_dialog_browser_manual -s -rPP
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    

    # test saving of config
    # =====================

    def dialog_input_sequence(dialog):    
        if os.environ.get('HYPERTTS_BATCH_DIALOG_DEBUG', 'no') == 'yes':
            dialog.exec()

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    component_batch.create_component_batch_browser_new_preset(hypertts_instance, note_id_list, 'my preset 1')


def test_text_processing(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')    

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    text_processing = component_text_processing.TextProcessing(hypertts_instance, model_change_callback.model_updated)
    dialog.addChildWidget(text_processing.draw())

    # dialog.exec()

    # asserts on the GUI
    assert text_processing.textReplacementTableModel.headerData(0, aqt.qt.Qt.Orientation.Horizontal, aqt.qt.Qt.ItemDataRole.DisplayRole) == 'Type'
    assert text_processing.textReplacementTableModel.headerData(1, aqt.qt.Qt.Orientation.Horizontal, aqt.qt.Qt.ItemDataRole.DisplayRole) == 'Pattern'
    assert text_processing.textReplacementTableModel.headerData(2, aqt.qt.Qt.Orientation.Horizontal, aqt.qt.Qt.ItemDataRole.DisplayRole) == 'Replacement'    
    # should have 0 rows
    assert text_processing.textReplacementTableModel.rowCount(None) == 0    

    # check processing preview
    qtbot.keyClicks(text_processing.sample_text_input, 'abdc1234')
    assert text_processing.sample_text_transformed_label.text() == '<b>abdc1234</b>'

    # add a text transformation rule
    qtbot.mouseClick(text_processing.add_replace_simple_button, aqt.qt.Qt.MouseButton.LeftButton)
    # enter pattern and replacement
    row = 0
    index_pattern = text_processing.textReplacementTableModel.createIndex(row, component_text_processing.COL_INDEX_PATTERN)
    text_processing.textReplacementTableModel.setData(index_pattern, '1234', aqt.qt.Qt.ItemDataRole.EditRole)
    index_replacement = text_processing.textReplacementTableModel.createIndex(row, component_text_processing.COL_INDEX_REPLACEMENT)
    text_processing.textReplacementTableModel.setData(index_replacement, '5678', aqt.qt.Qt.ItemDataRole.EditRole)

    # verify preview
    assert text_processing.sample_text_transformed_label.text() == '<b>abdc5678</b>'

    # add another transformation rule
    qtbot.mouseClick(text_processing.add_replace_simple_button, aqt.qt.Qt.MouseButton.LeftButton)
    # enter pattern and replacement
    row = 1
    index_pattern = text_processing.textReplacementTableModel.createIndex(row, component_text_processing.COL_INDEX_PATTERN)
    text_processing.textReplacementTableModel.setData(index_pattern, ' / ', aqt.qt.Qt.ItemDataRole.EditRole)
    index_replacement = text_processing.textReplacementTableModel.createIndex(row, component_text_processing.COL_INDEX_REPLACEMENT)
    text_processing.textReplacementTableModel.setData(index_replacement, ' ', aqt.qt.Qt.ItemDataRole.EditRole)

    # check processing preview
    text_processing.sample_text_input.clear()
    qtbot.keyClicks(text_processing.sample_text_input, 'word1 / word2')
    assert text_processing.sample_text_transformed_label.text() == '<b>word1 word2</b>'

    # check model callbacks
    assert len(model_change_callback.model.text_replacement_rules) == 2
    assert model_change_callback.model.text_replacement_rules[0].rule_type == constants.TextReplacementRuleType.Simple
    assert model_change_callback.model.text_replacement_rules[0].source == '1234'
    assert model_change_callback.model.text_replacement_rules[0].target == '5678'
    assert model_change_callback.model.text_replacement_rules[1].rule_type == constants.TextReplacementRuleType.Simple
    assert model_change_callback.model.text_replacement_rules[1].source == ' / '
    assert model_change_callback.model.text_replacement_rules[1].target == ' '

    # add a regex rule
    # add another transformation rule
    qtbot.mouseClick(text_processing.add_replace_regex_button, aqt.qt.Qt.MouseButton.LeftButton)
    # enter pattern and replacement
    row = 2
    index_pattern = text_processing.textReplacementTableModel.createIndex(row, component_text_processing.COL_INDEX_PATTERN)
    text_processing.textReplacementTableModel.setData(index_pattern, '[0-9]+', aqt.qt.Qt.ItemDataRole.EditRole)
    index_replacement = text_processing.textReplacementTableModel.createIndex(row, component_text_processing.COL_INDEX_REPLACEMENT)
    text_processing.textReplacementTableModel.setData(index_replacement, 'number', aqt.qt.Qt.ItemDataRole.EditRole)

    text_processing.sample_text_input.clear()
    qtbot.keyClicks(text_processing.sample_text_input, '1234')
    assert text_processing.sample_text_transformed_label.text() == '<b>number</b>'

    # check model callbacks
    assert len(model_change_callback.model.text_replacement_rules) == 3
    assert model_change_callback.model.text_replacement_rules[2].rule_type == constants.TextReplacementRuleType.Regex
    assert model_change_callback.model.text_replacement_rules[2].source == '[0-9]+'
    assert model_change_callback.model.text_replacement_rules[2].target == 'number'

    # do some other model callback checks
    text_processing.html_to_text_line_checkbox.setChecked(False)
    assert model_change_callback.model.html_to_text_line == False
    text_processing.html_to_text_line_checkbox.setChecked(True)
    assert model_change_callback.model.html_to_text_line == True
    text_processing.ssml_convert_characters_checkbox.setChecked(False)
    assert model_change_callback.model.ssml_convert_characters == False
    text_processing.run_replace_rules_after_checkbox.setChecked(False)
    assert model_change_callback.model.run_replace_rules_after == False    

    # default should be unchecked
    assert text_processing.strip_brackets_checkbox.isChecked() == False

    text_processing.strip_brackets_checkbox.setChecked(True)
    assert model_change_callback.model.strip_brackets == True
    text_processing.strip_brackets_checkbox.setChecked(False)
    assert model_change_callback.model.strip_brackets == False
    # ignore case
    text_processing.ignore_case_checkbox.setChecked(True)
    assert model_change_callback.model.ignore_case == True
    text_processing.ignore_case_checkbox.setChecked(False)
    assert model_change_callback.model.ignore_case == False


    # dialog.exec()


    # verify load_model
    # =================

    text_processing = config_models.TextProcessing()
    rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Simple)
    rule.source = 'a'
    rule.target = 'b'
    text_processing.add_text_replacement_rule(rule)
    rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Regex)
    rule.source = 'c'
    rule.target = 'd'    
    text_processing.add_text_replacement_rule(rule)

    text_processing.html_to_text_line = False
    text_processing.strip_brackets = True
    text_processing.ssml_convert_characters = True
    text_processing.run_replace_rules_after = False

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    text_processing_component = component_text_processing.TextProcessing(hypertts_instance, model_change_callback.model_updated)
    dialog.addChildWidget(text_processing_component.draw())
    text_processing_component.load_model(text_processing)

    # check first row
    row = 0
    index = text_processing_component.textReplacementTableModel.createIndex(row, component_text_processing.COL_INDEX_TYPE)
    rule_type = text_processing_component.textReplacementTableModel.data(index, aqt.qt.Qt.ItemDataRole.DisplayRole)
    assert rule_type.value() == 'Simple'
    index = text_processing_component.textReplacementTableModel.createIndex(row, component_text_processing.COL_INDEX_PATTERN)
    source = text_processing_component.textReplacementTableModel.data(index, aqt.qt.Qt.ItemDataRole.DisplayRole)
    assert source.value() == '"a"'
    index = text_processing_component.textReplacementTableModel.createIndex(row, component_text_processing.COL_INDEX_REPLACEMENT)
    target = text_processing_component.textReplacementTableModel.data(index, aqt.qt.Qt.ItemDataRole.DisplayRole)
    assert target.value() == '"b"'

    # check second row
    row = 1
    index = text_processing_component.textReplacementTableModel.createIndex(row, component_text_processing.COL_INDEX_TYPE)
    rule_type = text_processing_component.textReplacementTableModel.data(index, aqt.qt.Qt.ItemDataRole.DisplayRole)
    assert rule_type.value() == 'Regex'
    index = text_processing_component.textReplacementTableModel.createIndex(row, component_text_processing.COL_INDEX_PATTERN)
    source = text_processing_component.textReplacementTableModel.data(index, aqt.qt.Qt.ItemDataRole.DisplayRole)
    assert source.value() == '"c"'
    index = text_processing_component.textReplacementTableModel.createIndex(row, component_text_processing.COL_INDEX_REPLACEMENT)
    target = text_processing_component.textReplacementTableModel.data(index, aqt.qt.Qt.ItemDataRole.DisplayRole)
    assert target.value() == '"d"'    

    assert text_processing_component.html_to_text_line_checkbox.isChecked() == False
    assert text_processing_component.strip_brackets_checkbox.isChecked() == True
    assert text_processing_component.ssml_convert_characters_checkbox.isChecked() == True
    assert text_processing_component.run_replace_rules_after_checkbox.isChecked() == False

    # dialog.exec()

def test_text_processing_manual(qtbot):
    # HYPERTTS_TEXT_PROCESSING_DIALOG_DEBUG=yes pytest test_components.py -k test_text_processing_manual
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')    

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    text_processing = component_text_processing.TextProcessing(hypertts_instance, model_change_callback.model_updated)
    dialog.addChildWidget(text_processing.draw())

    if os.environ.get('HYPERTTS_TEXT_PROCESSING_DIALOG_DEBUG', 'no') == 'yes':
        dialog.exec()        

def test_configuration(qtbot):
    # pytest test_components.py -k test_configuration -o log_cli_level=DEBUG -o capture=no
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    # start by disabling both services
    hypertts_instance.service_manager.get_service('ServiceA').enabled = False
    hypertts_instance.service_manager.get_service('ServiceB').enabled = False

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # model_change_callback = gui_testing_utils.MockModelChangeCallback()
    configuration = component_configuration.Configuration(hypertts_instance, dialog)
    configuration.draw(dialog.getLayout())

    # dialog.exec()

    # try making changes to the service config and saving
    # ===================================================

    qtbot.mouseClick(configuration.hyperttspro.enter_api_key_button, aqt.qt.Qt.MouseButton.LeftButton)
    qtbot.keyClicks(configuration.hyperttspro.hypertts_pro_api_key, 'error_key')
    assert configuration.model.hypertts_pro_api_key == None

    assert configuration.hyperttspro.api_key_validation_label.text() == '<b>error</b>: Key invalid'

    # we entered an error key, so pro mode is not enabled
    assert configuration.service_stack_map['ServiceB'].isVisibleTo(dialog) == True
    assert configuration.clt_stack_map['ServiceB'].isVisibleTo(dialog) == False
    assert configuration.service_stack_map['ServiceA'].isVisibleTo(dialog) == True
    assert configuration.header_logo_stack_widget.currentIndex() == configuration.STACK_LEVEL_LITE

    service_a_enabled_checkbox = dialog.findChild(aqt.qt.QCheckBox, "ServiceA_enabled")
    service_a_enabled_checkbox.setChecked(True)
    assert configuration.model.get_service_enabled('ServiceA') == True
    service_a_enabled_checkbox.setChecked(False)
    assert configuration.model.get_service_enabled('ServiceA') == False

    service_a_region = dialog.findChild(aqt.qt.QComboBox, "ServiceA_region")
    service_a_region.setCurrentText('europe')
    assert configuration.model.get_service_configuration_key('ServiceA', 'region') == 'europe'
    service_a_region.setCurrentText('us')
    assert configuration.model.get_service_configuration_key('ServiceA', 'region') == 'us'
    
    service_a_api_key = dialog.findChild(aqt.qt.QLineEdit, "ServiceA_api_key")
    qtbot.keyClicks(service_a_api_key, '6789')
    assert configuration.model.get_service_configuration_key('ServiceA', 'api_key') == '6789'

    service_a_delay = dialog.findChild(aqt.qt.QSpinBox, "ServiceA_delay")
    service_a_delay.setValue(42)
    assert configuration.model.get_service_configuration_key('ServiceA', 'delay') == 42

    service_a_demokey = dialog.findChild(aqt.qt.QCheckBox, "ServiceA_demo_key")
    service_a_demokey.setChecked(True)
    assert configuration.model.get_service_configuration_key('ServiceA', 'demo_key') == True
    service_a_demokey.setChecked(False)
    assert configuration.model.get_service_configuration_key('ServiceA', 'demo_key') == False
    service_a_demokey.setChecked(True)

    assert configuration.save_button.isEnabled() == True

    # press save button
    qtbot.mouseClick(configuration.save_button, aqt.qt.Qt.MouseButton.LeftButton)
    assert 'configuration' in hypertts_instance.anki_utils.written_config
    expected_output = {
        'hypertts_pro_api_key': None,
        'use_vocabai_api': False, 
        'vocabai_api_url_override': None,
        'service_enabled': {
            'ServiceA': False,
        },
        'service_config': {
            'ServiceA': {
                'region': 'us',
                'api_key': '6789',
                'delay': 42,
                'demo_key': True
            },
        }
    }
    assert hypertts_instance.anki_utils.written_config['configuration'] == expected_output

    # make sure dialog was closed
    assert dialog.closed == True

    # enter valid API key
    # ===================

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    configuration = component_configuration.Configuration(hypertts_instance, dialog)
    configuration.draw(dialog.getLayout())

    qtbot.mouseClick(configuration.hyperttspro.enter_api_key_button, aqt.qt.Qt.MouseButton.LeftButton)
    qtbot.keyClicks(configuration.hyperttspro.hypertts_pro_api_key, 'valid_key')
    assert '250 chars' in configuration.hyperttspro.account_info_label.text()

    assert configuration.service_stack_map['ServiceB'].isVisibleTo(dialog) == False
    assert configuration.clt_stack_map['ServiceB'].isVisibleTo(dialog) == True # clt displayed
    assert configuration.service_stack_map['ServiceA'].isVisibleTo(dialog) == True
    assert configuration.header_logo_stack_widget.currentIndex() == configuration.STACK_LEVEL_PRO

    assert configuration.model.hypertts_pro_api_key == 'valid_key'

    # switch to an invalid key
    # remove key first
    qtbot.mouseClick(configuration.hyperttspro.remove_api_key_button, aqt.qt.Qt.MouseButton.LeftButton)
    qtbot.mouseClick(configuration.hyperttspro.enter_api_key_button, aqt.qt.Qt.MouseButton.LeftButton)
    configuration.hyperttspro.hypertts_pro_api_key.setText('invalid_key')
    assert configuration.model.hypertts_pro_api_key == None
    assert configuration.service_stack_map['ServiceB'].isVisibleTo(dialog) == True
    assert configuration.clt_stack_map['ServiceB'].isVisibleTo(dialog) == False
    assert configuration.service_stack_map['ServiceA'].isVisibleTo(dialog) == True
    assert configuration.header_logo_stack_widget.currentIndex() == configuration.STACK_LEVEL_LITE

    assert configuration.hyperttspro.api_key_validation_label.text() == '<b>error</b>: Key invalid'

    # dialog.exec()

    # loading of existing model, no pro api key
    # =========================================

    configuration_model = config_models.Configuration()
    configuration_model.set_hypertts_pro_api_key(None)
    configuration_model.set_service_enabled('ServiceB', True)
    configuration_model.set_service_configuration_key('ServiceA', 'api_key', '123456')
    configuration_model.set_service_configuration_key('ServiceA', 'region', 'europe')
    configuration_model.set_service_configuration_key('ServiceA', 'delay', 7)
    configuration_model.set_service_configuration_key('ServiceA', 'demo_key', True)

    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    # start by disabling both services
    hypertts_instance.service_manager.get_service('ServiceA').enabled = False
    hypertts_instance.service_manager.get_service('ServiceB').enabled = False
    hypertts_instance.service_manager.configure(configuration_model)

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    configuration = component_configuration.Configuration(hypertts_instance, dialog)
    configuration.load_model(configuration_model)
    configuration.draw(dialog.getLayout())

    assert configuration.hyperttspro.hypertts_pro_api_key.text() == ''

    assert configuration.service_stack_map['ServiceB'].isVisibleTo(dialog) == True
    assert configuration.service_stack_map['ServiceA'].isVisibleTo(dialog) == True
    assert configuration.header_logo_stack_widget.currentIndex() == configuration.STACK_LEVEL_LITE

    service_a_enabled_checkbox = dialog.findChild(aqt.qt.QCheckBox, "ServiceA_enabled")
    assert service_a_enabled_checkbox.isChecked() == False
    service_b_enabled_checkbox = dialog.findChild(aqt.qt.QCheckBox, "ServiceB_enabled")
    assert service_b_enabled_checkbox.isChecked() == True

    service_a_region = dialog.findChild(aqt.qt.QComboBox, "ServiceA_region")
    assert service_a_region.currentText() == 'europe'
    service_a_api_key = dialog.findChild(aqt.qt.QLineEdit, "ServiceA_api_key")
    assert service_a_api_key.text() == '123456'
    service_a_delay = dialog.findChild(aqt.qt.QSpinBox, "ServiceA_delay")
    assert service_a_delay.value() == 7
    service_a_demokey = dialog.findChild(aqt.qt.QCheckBox, "ServiceA_demo_key")
    assert service_a_demokey.isChecked() == True

    # setting the API key should make ServiceB's enable checkbox disabled and checked
    service_b_enabled_checkbox = dialog.findChild(aqt.qt.QCheckBox, "ServiceB_enabled")
    assert service_b_enabled_checkbox.isChecked() == True

    assert configuration.save_button.isEnabled() == False

    # dialog.exec()

    # loading of existing model, with valid pro API key
    # =================================================

    configuration_model = config_models.Configuration()
    configuration_model.set_hypertts_pro_api_key('valid_key')

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    configuration = component_configuration.Configuration(hypertts_instance, dialog)
    configuration.load_model(configuration_model)
    configuration.draw(dialog.getLayout())

    # dialog.exec()
    assert configuration.hyperttspro.hypertts_pro_stack.currentIndex() == configuration.hyperttspro.PRO_STACK_LEVEL_ENABLED
    assert configuration.hyperttspro.api_key_label.text() == '<b>API Key:</b> valid_key'

    assert configuration.header_logo_stack_widget.currentIndex() == configuration.STACK_LEVEL_PRO
    assert configuration.clt_stack_map['ServiceB'].isVisibleTo(dialog) == True
    assert configuration.service_stack_map['ServiceA'].isVisibleTo(dialog) == True

    assert configuration.save_button.isEnabled() == False # since we didn't change anything

    # dialog.exec()    

def test_configuration_pro_key_exception(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    # start by disabling both services
    hypertts_instance.service_manager.get_service('ServiceA').enabled = False
    hypertts_instance.service_manager.get_service('ServiceB').enabled = False

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # model_change_callback = gui_testing_utils.MockModelChangeCallback()
    configuration = component_configuration.Configuration(hypertts_instance, dialog)
    configuration.draw(dialog.getLayout())

    # dialog.exec()

    # try making changes to the service config and saving
    # ===================================================

    qtbot.keyClicks(configuration.hyperttspro.hypertts_pro_api_key, 'exception_key')
    assert configuration.model.hypertts_pro_api_key == None

    # assert configuration.account_info_label.text() == '<b>error</b>: Key invalid'

    # we entered an error key, so pro mode is not enabled
    assert configuration.service_stack_map['ServiceB'].isVisibleTo(dialog) == True
    assert configuration.clt_stack_map['ServiceB'].isVisibleTo(dialog) == False
    assert configuration.service_stack_map['ServiceA'].isVisibleTo(dialog) == True
    assert configuration.header_logo_stack_widget.currentIndex() == configuration.STACK_LEVEL_LITE

def test_configuration_enable_disable_services(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    # start by disabling both services
    hypertts_instance.service_manager.get_service('ServiceA').enabled = False
    hypertts_instance.service_manager.get_service('ServiceB').enabled = False

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # model_change_callback = gui_testing_utils.MockModelChangeCallback()
    configuration = component_configuration.Configuration(hypertts_instance, dialog)
    configuration.draw(dialog.getLayout())

    # enable all free services
    # ========================
    qtbot.mouseClick(configuration.enable_all_free_services_button, aqt.qt.Qt.MouseButton.LeftButton)

    # check effect on model
    assert configuration.model.get_service_enabled('ServiceA') == True

    # now enable services B and C
    # ============================
    checkbox = dialog.findChild(aqt.qt.QCheckBox, "ServiceB_enabled")
    checkbox.setChecked(True)    
    checkbox = dialog.findChild(aqt.qt.QCheckBox, "ServiceC_enabled")
    checkbox.setChecked(True)

    assert configuration.model.get_service_enabled('ServiceA') == True
    assert configuration.model.get_service_enabled('ServiceB') == True
    assert configuration.model.get_service_enabled('ServiceC') == True

    # now disable all services
    # ========================
    qtbot.mouseClick(configuration.disable_all_services_button, aqt.qt.Qt.MouseButton.LeftButton)
    assert configuration.model.get_service_enabled('ServiceA') == False
    assert configuration.model.get_service_enabled('ServiceB') == False
    assert configuration.model.get_service_enabled('ServiceC') == False   


def test_configuration_manual(qtbot):
    # HYPERTTS_CONFIGURATION_DIALOG_DEBUG=yes pytest test_components.py -k test_configuration_manual
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
    # start by disabling both services
    hypertts_instance.service_manager.get_service('ServiceA').enabled = False
    hypertts_instance.service_manager.get_service('ServiceB').enabled = False

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # model_change_callback = gui_testing_utils.MockModelChangeCallback()
    configuration = component_configuration.Configuration(hypertts_instance, dialog)
    configuration.draw(dialog.getLayout())    

    if os.environ.get('HYPERTTS_CONFIGURATION_DIALOG_DEBUG', 'no') == 'yes':
        dialog.exec()    

def test_hyperttspro_test_1(qtbot):
    # pytest test_components.py -k test_hyperttspro_test_1
    # pytest test_components.py -k test_hyperttspro_test_1 -o log_cli_level=DEBUG -o capture=no
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    model_change_callback = gui_testing_utils.MockModelChangeCallback()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    hyperttspro = component_hyperttspro.HyperTTSPro(hypertts_instance, model_change_callback.model_updated)
    hyperttspro.draw(dialog.getLayout())

    # enter API key
    # =============

    # enter API key
    qtbot.mouseClick(hyperttspro.enter_api_key_button, aqt.qt.Qt.MouseButton.LeftButton)
    # ensure the right stack is visible
    assert hyperttspro.hypertts_pro_stack.currentIndex() == hyperttspro.PRO_STACK_LEVEL_API_KEY
    assert model_change_callback.model == None
    # click cancel
    qtbot.mouseClick(hyperttspro.enter_api_key_cancel_button, aqt.qt.Qt.MouseButton.LeftButton)
    # back in the main screen
    assert hyperttspro.hypertts_pro_stack.currentIndex() == hyperttspro.PRO_STACK_LEVEL_BUTTONS
    assert model_change_callback.model == None
    # now actual enter a valid API key
    qtbot.mouseClick(hyperttspro.enter_api_key_button, aqt.qt.Qt.MouseButton.LeftButton)
    qtbot.keyClicks(hyperttspro.hypertts_pro_api_key, 'valid_key')
    # should now be in the enabled screen
    assert hyperttspro.hypertts_pro_stack.currentIndex() == hyperttspro.PRO_STACK_LEVEL_ENABLED
    assert hyperttspro.api_key_label.text() == '<b>API Key:</b> valid_key'
    assert model_change_callback.model == config_models.HyperTTSProAccountConfig(
        api_key='valid_key',
        api_key_valid=True,
        use_vocabai_api=False,
        api_key_error=None,
        account_info={
                'type': '250 chars',
                'email': 'no@spam.com',
                'update_url': 'https://www.vocab.ai/awesometts-plus',
                'cancel_url': 'https://www.vocab.ai/awesometts-plus'
            }
    )

    # now remove the API key
    qtbot.mouseClick(hyperttspro.remove_api_key_button, aqt.qt.Qt.MouseButton.LeftButton)
    assert hyperttspro.hypertts_pro_stack.currentIndex() == hyperttspro.PRO_STACK_LEVEL_BUTTONS
    assert model_change_callback.model == config_models.HyperTTSProAccountConfig(
        api_key=None,
        api_key_valid=False,
        use_vocabai_api=False,
        api_key_error=None,
        account_info=None
    )

    # go back to enter API key screen
    qtbot.mouseClick(hyperttspro.enter_api_key_button, aqt.qt.Qt.MouseButton.LeftButton)
    assert hyperttspro.hypertts_pro_api_key.text() == ''
    assert hyperttspro.api_key_validation_label.text() == ''

    # enter invalid api key
    qtbot.keyClicks(hyperttspro.hypertts_pro_api_key, 'invalid_key')
    assert hyperttspro.api_key_validation_label.text() == '<b>error</b>: Key invalid'
    assert hyperttspro.hypertts_pro_stack.currentIndex() == hyperttspro.PRO_STACK_LEVEL_API_KEY
    assert model_change_callback.model == config_models.HyperTTSProAccountConfig(
        api_key_error='Key invalid',
    )

    # cancel
    qtbot.mouseClick(hyperttspro.enter_api_key_cancel_button, aqt.qt.Qt.MouseButton.LeftButton)
    assert model_change_callback.model == config_models.HyperTTSProAccountConfig(
        api_key_error='Key invalid',
    )

    # load_model with a valid API key
    # ===============================

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    hyperttspro = component_hyperttspro.HyperTTSPro(hypertts_instance, model_change_callback.model_updated)
    model = config_models.HyperTTSProAccountConfig(
        api_key='valid_key')
    hyperttspro.load_model(model)
    hyperttspro.draw(dialog.getLayout())

    assert hyperttspro.hypertts_pro_stack.currentIndex() == hyperttspro.PRO_STACK_LEVEL_ENABLED
    assert hyperttspro.api_key_label.text() == '<b>API Key:</b> valid_key'
    assert model_change_callback.model == config_models.HyperTTSProAccountConfig(
        api_key='valid_key',
        api_key_valid=True,
        account_info={
                'type': '250 chars',
                'email': 'no@spam.com',
                'update_url': 'https://www.vocab.ai/awesometts-plus',
                'cancel_url': 'https://www.vocab.ai/awesometts-plus'
            }        )

    # load with an invalid API key
    # ============================

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    hyperttspro = component_hyperttspro.HyperTTSPro(hypertts_instance, model_change_callback.model_updated)
    model = config_models.HyperTTSProAccountConfig(
        api_key='invalid_key')    
    hyperttspro.load_model(model)
    hyperttspro.draw(dialog.getLayout())

    assert hyperttspro.hypertts_pro_stack.currentIndex() == hyperttspro.PRO_STACK_LEVEL_API_KEY
    assert hyperttspro.hypertts_pro_api_key.text() == 'invalid_key'
    assert hyperttspro.api_key_validation_label.text() == '<b>error</b>: Key invalid'
    assert model_change_callback.model == config_models.HyperTTSProAccountConfig(
        api_key_error='Key invalid',
    )
    # dialog.exec()

    # request trial key by email
    # ==========================

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    hyperttspro = component_hyperttspro.HyperTTSPro(hypertts_instance, model_change_callback.model_updated)
    hyperttspro.draw(dialog.getLayout())    

    qtbot.mouseClick(hyperttspro.trial_button, aqt.qt.Qt.MouseButton.LeftButton)
    
    # enter incorrect email
    logger.info('entering incorrect email for trial signup')
    model_change_callback.model = None
    assert hyperttspro.hypertts_pro_stack.currentIndex() == hyperttspro.PRO_STACK_LEVEL_TRIAL
    qtbot.keyClicks(hyperttspro.trial_email_input, 'spam@spam.com')    
    qtbot.mouseClick(hyperttspro.enter_trial_email_ok_button, aqt.qt.Qt.MouseButton.LeftButton)
    assert hyperttspro.hypertts_pro_stack.currentIndex() == hyperttspro.PRO_STACK_LEVEL_TRIAL
    assert hyperttspro.trial_email_validation_label.text() == 'invalid email'
    assert model_change_callback.model == None

    # enter correct email
    hyperttspro.trial_email_input.setText('')
    qtbot.keyClicks(hyperttspro.trial_email_input, 'valid@email.com')    
    qtbot.mouseClick(hyperttspro.enter_trial_email_ok_button, aqt.qt.Qt.MouseButton.LeftButton)    
    assert hyperttspro.hypertts_pro_stack.currentIndex() == hyperttspro.PRO_STACK_LEVEL_ENABLED
    assert model_change_callback.model == config_models.HyperTTSProAccountConfig(
        api_key='trial_key',
        api_key_valid=True, 
        use_vocabai_api=False, 
        api_key_error=None, 
        account_info={'type': 'trial', 'email': 'no@spam.com'}
    )
    model_change_callback.model = None

    # dialog.exec()


    # enter invalid key, then delete it
    # =================================

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    hyperttspro = component_hyperttspro.HyperTTSPro(hypertts_instance, model_change_callback.model_updated)
    hyperttspro.draw(dialog.getLayout())

    # enter API key
    # =============

    # enter invalid api key (must click the button first)
    qtbot.mouseClick(hyperttspro.enter_api_key_button, aqt.qt.Qt.MouseButton.LeftButton)    
    qtbot.keyClicks(hyperttspro.hypertts_pro_api_key, 'invalid_key')
    assert hyperttspro.api_key_validation_label.text() == '<b>error</b>: Key invalid'
    assert hyperttspro.hypertts_pro_stack.currentIndex() == hyperttspro.PRO_STACK_LEVEL_API_KEY
    assert model_change_callback.model == config_models.HyperTTSProAccountConfig(
        api_key_valid=False,
        api_key_error='Key invalid'
    )    
    model_change_callback.model = None

    # now remove this incorrect API key
    hyperttspro.hypertts_pro_api_key.setText('')
    assert hyperttspro.api_key_validation_label.text() == '<b>error</b>: please enter API key'
    assert hyperttspro.hypertts_pro_stack.currentIndex() == hyperttspro.PRO_STACK_LEVEL_API_KEY
    assert model_change_callback.model == None        




def test_hyperttspro_manual(qtbot):
    # HYPERTTS_PRO_DIALOG_DEBUG=yes pytest test_components.py -k test_hyperttspro_manual
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    model_change_callback = gui_testing_utils.MockModelChangeCallback()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    hyperttspro = component_hyperttspro.HyperTTSPro(hypertts_instance, model_change_callback.model_updated)
    hyperttspro.draw(dialog.getLayout())

    if os.environ.get('HYPERTTS_PRO_DIALOG_DEBUG', 'no') == 'yes':
        dialog.exec()            

def test_batch_dialog_load_random(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    

    # test saving of config
    # =====================

    def dialog_input_sequence(dialog):
        # select a source field and target field
        dialog.batch_component.source.source_field_combobox.setCurrentText('English')
        dialog.batch_component.target.target_field_combobox.setCurrentText('Sound')
        
        # select random voice selection mode with two voices
        dialog.batch_component.voice_selection.radio_button_random.setChecked(True)
        # pick second voice and add it
        testing_utils.voice_selection_voice_list_select('voice_a_1', 'ServiceA', dialog.batch_component.voice_selection.voices_combobox)
        # dialog.batch_component.voice_selection.voices_combobox.setCurrentIndex(1) # pick second voice
        qtbot.mouseClick(dialog.batch_component.voice_selection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)
        # pick third voice and add it
        # dialog.batch_component.voice_selection.voices_combobox.setCurrentIndex(2) # pick second voice
        testing_utils.voice_selection_voice_list_select('voice_a_2', 'ServiceA', dialog.batch_component.voice_selection.voices_combobox)
        qtbot.mouseClick(dialog.batch_component.voice_selection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)

        # set profile name
        preset_name = 'batch random 1'
        hypertts_instance.anki_utils.ask_user_get_text_response = preset_name
        qtbot.mouseClick(dialog.batch_component.profile_rename_button, aqt.qt.Qt.MouseButton.LeftButton)
        # save
        qtbot.mouseClick(dialog.batch_component.profile_save_button, aqt.qt.Qt.MouseButton.LeftButton)

        assert 'uuid_1' in hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS]

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    component_batch.create_component_batch_browser_new_preset(hypertts_instance, note_id_list, 'my preset 1')


    # test loading of config
    # ======================

    def dialog_input_sequence(dialog):
        # dialog.exec()
        assert dialog.batch_component.profile_open_button.isEnabled() == True
        hypertts_instance.anki_utils.ask_user_choose_from_list_response_string = 'batch random 1'
        # click the open profile button
        qtbot.mouseClick(dialog.batch_component.profile_open_button, aqt.qt.Qt.MouseButton.LeftButton)

        # save button should be disabled
        assert dialog.batch_component.profile_save_button.isEnabled() == False

        # check that the voice selection mode is random
        assert dialog.batch_component.get_model().voice_selection.selection_mode == constants.VoiceSelectionMode.random
        assert len(dialog.batch_component.get_model().voice_selection.get_voice_list()) == 2

        # apply to notes
        qtbot.mouseClick(dialog.batch_component.apply_button, aqt.qt.Qt.MouseButton.LeftButton)

        # ensure audio was applied to 2 notes
        # make sure notes were updated
        note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
        assert 'Sound' in note_1.set_values 
        note_2 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_2)
        assert 'Sound' in note_2.set_values     

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    component_batch.create_component_batch_browser_new_preset(hypertts_instance, note_id_list, 'my preset 1')

    # test that changing random weights enables the save button
    # =========================================================

    def dialog_input_sequence(dialog):
        # dialog.exec()
        assert dialog.batch_component.profile_open_button.isEnabled() == True
        hypertts_instance.anki_utils.ask_user_choose_from_list_response_string = 'batch random 1'
        # click the open profile button
        qtbot.mouseClick(dialog.batch_component.profile_open_button, aqt.qt.Qt.MouseButton.LeftButton)

        # save button should be disabled
        assert dialog.batch_component.profile_save_button.isEnabled() == False

        # check that the voice selection mode is random
        assert dialog.batch_component.get_model().voice_selection.selection_mode == constants.VoiceSelectionMode.random
        assert len(dialog.batch_component.get_model().voice_selection.get_voice_list()) == 2

        # change random weight of one of the voices
        logger.debug(f'changing random weight of second voice')
        random_voice_index = 1 # second voice
        widget_row = random_voice_index
        widget_column = 1
        weight_widget = dialog.batch_component.voice_selection.voice_list_grid_layout.itemAtPosition(widget_row, widget_column).widget()
        weight_widget.setValue(42)
        logger.debug(f'weight_widget.value: {weight_widget.value}')

        # ensure that model got updated with the new weight
        assert dialog.batch_component.get_model().voice_selection.get_voice_list()[random_voice_index].random_weight == 42

        # save button should be enabled
        assert dialog.batch_component.profile_save_button.isEnabled() == True, "save button enabled after changing random weight"

    hypertts_instance.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = dialog_input_sequence
    component_batch.create_component_batch_browser_new_preset(hypertts_instance, note_id_list, 'my preset 1')

    # dialog.exec()

def test_realtime_source(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')    

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    note_id_list = [config_gen.note_id_1]

    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    field_list = hypertts_instance.get_all_fields_from_notes(note_id_list)
    source = component_realtime_source.RealtimeSource(hypertts_instance, field_list, model_change_callback.model_updated)
    dialog.addChildWidget(source.draw())

    # dialog.exec()

    expected_source_model = config_models.RealtimeSourceAnkiTTS()
    expected_source_model.field_name = 'Chinese'
    expected_source_model.field_type = constants.AnkiTTSFieldType.Regular

    assert source.get_model().serialize() == expected_source_model.serialize()

    # select different field
    source.source_field_combobox.setCurrentText('English')
    expected_source_model.field_name = 'English'
    assert model_change_callback.model.serialize() == expected_source_model.serialize()

    # select different field type
    source.source_field_type_combobox.setCurrentText(constants.AnkiTTSFieldType.Cloze.name)
    expected_source_model.field_type = constants.AnkiTTSFieldType.Cloze
    assert model_change_callback.model.serialize() == expected_source_model.serialize()

    # load config
    # ===========
    source_model = config_models.RealtimeSourceAnkiTTS()
    source_model.field_name = 'Pinyin'
    source_model.field_type = constants.AnkiTTSFieldType.Cloze 

    source.load_model(source_model)
    assert source.source_type_combobox.currentText() == 'AnkiTTSTag'
    assert source.source_field_combobox.currentText() == 'Pinyin'
    assert source.source_field_type_combobox.currentText() == 'Cloze'


def test_realtime_side_component(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()


    # initialize dialog
    # =================

    def existing_preset_fn(preset_name):
        pass

    note_id = config_gen.note_id_1
    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    realtime_side = component_realtime_side.ComponentRealtimeSide(hypertts_instance, dialog,
        constants.AnkiCardSide.Front, 0, model_change_callback.model_updated, existing_preset_fn)
    realtime_side.configure_note(note_1)
    dialog.addChildLayout(realtime_side.draw())

    # some initial checks
    assert realtime_side.get_model().side_enabled == False
    assert realtime_side.side_enabled_checkbox.isChecked() == False    
    assert realtime_side.tabs.isEnabled() == False
    assert realtime_side.preview_groupbox.isEnabled() == False

    # enable this side
    realtime_side.side_enabled_checkbox.setChecked(True)
    assert model_change_callback.model.side_enabled == True
    assert realtime_side.tabs.isEnabled() == True
    assert realtime_side.preview_groupbox.isEnabled() == True

    # dialog.exec()

    # the chinese text should be in the preview (default text)
    assert model_change_callback.model.source.field_name == 'Chinese'
    assert realtime_side.text_preview_label.text() == '老人家'

    # select a field
    realtime_side.source.source_field_combobox.setCurrentText('English')
    assert model_change_callback.model.source.field_name == 'English'
    # preview should be updated
    assert realtime_side.text_preview_label.text() == 'old people'

    # select voice
    testing_utils.voice_selection_voice_list_select('voice_a_1', 'ServiceA', realtime_side.voice_selection.voices_combobox)

    # press sound preview
    qtbot.mouseClick(realtime_side.preview_sound_button, aqt.qt.Qt.MouseButton.LeftButton)

    # ensure sound was played
    assert hypertts_instance.anki_utils.played_sound == {
        'source_text': 'old people',
        'voice': {
            'gender': 'Male', 
            'audio_languages': ['fr_FR'],
            'name': 'voice_a_1', 
            'service': 'ServiceA',
            'voice_key': {'name': 'voice_1'},
            'service_fee': 'free',
        },
        'options': {}
    }        
    
    # add text processing rule
    # ========================

    # add a text transformation rule
    qtbot.mouseClick(realtime_side.text_processing.add_replace_simple_button, aqt.qt.Qt.MouseButton.LeftButton)

    # enter pattern and replacement
    row = 0
    index_pattern = realtime_side.text_processing.textReplacementTableModel.createIndex(row, component_text_processing.COL_INDEX_PATTERN)
    realtime_side.text_processing.textReplacementTableModel.setData(index_pattern, 'old', aqt.qt.Qt.ItemDataRole.EditRole)
    index_replacement = realtime_side.text_processing.textReplacementTableModel.createIndex(row, component_text_processing.COL_INDEX_REPLACEMENT)
    realtime_side.text_processing.textReplacementTableModel.setData(index_replacement, 'young', aqt.qt.Qt.ItemDataRole.EditRole)

    # preview should be updated
    assert realtime_side.text_preview_label.text() == 'young people'

    # dialog.exec()

def test_realtime_component_single_voice(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # instantiate dialog
    # ==================

    note_id = config_gen.note_id_1
    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    realtime = component_realtime.ComponentRealtime(hypertts_instance, dialog, 0)
    realtime.configure_note(note_1)
    realtime.draw(dialog.getLayout())

    # enable TTS on each side
    # =======================

    assert realtime.apply_button.isEnabled() == False

    # enable front side, select a field
    realtime.front.side_enabled_checkbox.setChecked(True)
    realtime.front.source.source_field_combobox.setCurrentText('English')

    assert realtime.get_model().front.side_enabled == True
    assert realtime.get_model().front.source.field_name == 'English'
    assert realtime.get_model().front.source.field_type == constants.AnkiTTSFieldType.Regular

    testing_utils.voice_selection_voice_list_select('voice_a_1', 'ServiceA', realtime.front.voice_selection.voices_combobox)

    # enable back side
    realtime.back.side_enabled_checkbox.setChecked(True)
    realtime.back.source.source_field_combobox.setCurrentText('Chinese')
    assert realtime.get_model().back.side_enabled == True
    assert realtime.get_model().back.source.field_name == 'Chinese'

    testing_utils.voice_selection_voice_list_select('voice_a_1', 'ServiceA', realtime.back.voice_selection.voices_combobox)

    # click apply
    assert realtime.apply_button.isEnabled() == True
    qtbot.mouseClick(realtime.apply_button, aqt.qt.Qt.MouseButton.LeftButton)

    # assertions on config saved
    assert constants.CONFIG_REALTIME_CONFIG in hypertts_instance.anki_utils.written_config
    assert 'realtime_0' in hypertts_instance.anki_utils.written_config[constants.CONFIG_REALTIME_CONFIG]

    realtime_config_saved = hypertts_instance.anki_utils.written_config[constants.CONFIG_REALTIME_CONFIG]['realtime_0']
    assert realtime_config_saved['front']['source']['field_name'] == 'English'
    assert realtime_config_saved['back']['source']['field_name'] == 'Chinese'

    # pprint.pprint(hypertts_instance.anki_utils.written_config)

    # assertions on note type updated
    assert hypertts_instance.anki_utils.updated_note_model != None
    question_format = hypertts_instance.anki_utils.updated_note_model['tmpls'][0]['qfmt'].replace('\n', ' ')
    answer_format = hypertts_instance.anki_utils.updated_note_model['tmpls'][0]['afmt'].replace('\n', ' ')

    expected_front_tts_tag = '{{tts fr_FR hypertts_preset=Front_realtime_0 voices=HyperTTS:English}}'
    expected_back_tts_tag = '{{tts fr_FR hypertts_preset=Back_realtime_0 voices=HyperTTS:Chinese}}'

    # dialog.exec()

    assert expected_front_tts_tag in question_format
    assert expected_back_tts_tag in answer_format

    pprint.pprint(hypertts_instance.anki_utils.updated_note_model)

    # try to load an existing configuration
    # =====================================

    logger.info('loading an existing realtime configuration')

    # patch the config
    hypertts_instance.anki_utils.config[constants.CONFIG_REALTIME_CONFIG] = hypertts_instance.anki_utils.written_config[constants.CONFIG_REALTIME_CONFIG]

    # patch the templates
    # note_1.note_type()['tmpls'][0]['qfmt'] += '\n' + expected_front_tts_tag
    # note_1.note_type()['tmpls'][0]['afmt'] += '\n' + expected_back_tts_tag

    pprint.pprint(note_1.note_type())

    # launch dialog
    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    realtime = component_realtime.ComponentRealtime(hypertts_instance, dialog, 0)
    realtime.configure_note(note_1)
    realtime.draw(dialog.getLayout())    
    realtime.load_existing_preset()

    # we haven't changed anything at this point
    assert realtime.apply_button.isEnabled() == False

    assert realtime.front.side_enabled_checkbox.isChecked() == True
    assert realtime.front.source.source_field_combobox.currentText() == 'English'
    assert realtime.front.text_preview_label.text() == 'old people'

    assert realtime.back.side_enabled_checkbox.isChecked() == True
    assert realtime.back.source.source_field_combobox.currentText() == 'Chinese'
    assert realtime.back.text_preview_label.text() == '老人家'

    # disable the front TTS tag
    realtime.front.side_enabled_checkbox.setChecked(False)

    # save
    qtbot.mouseClick(realtime.apply_button, aqt.qt.Qt.MouseButton.LeftButton)

    # assertions on config saved
    assert constants.CONFIG_REALTIME_CONFIG in hypertts_instance.anki_utils.written_config
    assert 'realtime_0' in hypertts_instance.anki_utils.written_config[constants.CONFIG_REALTIME_CONFIG]

    realtime_config_saved = hypertts_instance.anki_utils.written_config[constants.CONFIG_REALTIME_CONFIG]['realtime_0']
    assert realtime_config_saved['front']['side_enabled'] == False

    # assertions on note type updated
    assert hypertts_instance.anki_utils.updated_note_model != None
    assert '{{tts' not in hypertts_instance.anki_utils.updated_note_model['tmpls'][0]['qfmt']

def test_realtime_component_priority_front(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # instantiate dialog
    # ==================

    note_id = config_gen.note_id_1
    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    realtime = component_realtime.ComponentRealtime(hypertts_instance, dialog, 0)
    realtime.configure_note(note_1)
    realtime.draw(dialog.getLayout())

    # enable TTS on each side
    # =======================

    assert realtime.apply_button.isEnabled() == False

    # enable front side, select a field
    realtime.front.side_enabled_checkbox.setChecked(True)
    realtime.front.source.source_field_combobox.setCurrentText('English')

    assert realtime.get_model().front.side_enabled == True
    assert realtime.get_model().front.source.field_name == 'English'
    assert realtime.get_model().front.source.field_type == constants.AnkiTTSFieldType.Regular

    testing_utils.voice_selection_voice_list_select('voice_a_2', 'ServiceA', realtime.front.voice_selection.voices_combobox)
    # select priority mode
    realtime.front.voice_selection.radio_button_priority.setChecked(True)
    # add voice
    qtbot.mouseClick(realtime.front.voice_selection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)

    # select another voice
    testing_utils.voice_selection_voice_list_select('voice_a_1', 'ServiceA', realtime.front.voice_selection.voices_combobox)
    # add voice
    qtbot.mouseClick(realtime.front.voice_selection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)

    # check resulting model
    assert realtime.get_model().front.voice_selection.selection_mode == constants.VoiceSelectionMode.priority
    assert len(realtime.get_model().front.voice_selection.voice_list) == 2

    # check TTS tag
    # =============
    # click apply
    assert realtime.apply_button.isEnabled() == True
    qtbot.mouseClick(realtime.apply_button, aqt.qt.Qt.MouseButton.LeftButton)

    # assertions on config saved
    assert constants.CONFIG_REALTIME_CONFIG in hypertts_instance.anki_utils.written_config
    assert 'realtime_0' in hypertts_instance.anki_utils.written_config[constants.CONFIG_REALTIME_CONFIG]

    realtime_config_saved = hypertts_instance.anki_utils.written_config[constants.CONFIG_REALTIME_CONFIG]['realtime_0']
    assert realtime_config_saved['front']['source']['field_name'] == 'English'

    # pprint.pprint(hypertts_instance.anki_utils.written_config)

    # assertions on note type updated
    assert hypertts_instance.anki_utils.updated_note_model != None
    question_format = hypertts_instance.anki_utils.updated_note_model['tmpls'][0]['qfmt'].replace('\n', ' ')

    # the language should be that of the first voice
    expected_front_tts_tag = '{{tts en_US hypertts_preset=Front_realtime_0 voices=HyperTTS:English}}'

    # dialog.exec()

    assert expected_front_tts_tag in question_format


def test_realtime_component_manual(qtbot):
    # HYPERTTS_REALTIME_DIALOG_DEBUG=yes pytest test_components.py -k test_realtime_component_manual -s -rPP
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()

    # instantiate dialog
    # ==================

    note_id = config_gen.note_id_1
    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    realtime = component_realtime.ComponentRealtime(hypertts_instance, dialog, 0)
    realtime.configure_note(note_1)
    realtime.draw(dialog.getLayout())    

    if os.environ.get('HYPERTTS_REALTIME_DIALOG_DEBUG', 'no') == 'yes':
        dialog.exec()    

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

    # try to make a change
    # ====================

    error_handling.realtime_tts_errors_dialog_type.setCurrentText('Nothing')
    assert model_change_callback.model.realtime_tts_errors_dialog_type == constants.ErrorDialogType.Nothing


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


