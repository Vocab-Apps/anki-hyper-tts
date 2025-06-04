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

