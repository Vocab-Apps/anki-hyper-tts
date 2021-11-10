import unittest
import pytest
import pprint
import logging
import PyQt5

import dialogs
import dialog_languagemapping
import dialog_voiceselection
import dialog_choosetranslation
import dialog_batchtransformation
import dialog_apikey
import dialog_textprocessing
import dialog_breakdown
import dialog_notesettings
import languagetools
import constants
import testing_utils
import deck_utils
import errors

def assert_combobox_items_equal(combobox, expected_items):
    combobox_items = []
    for i in range(combobox.count()):
        combobox_items.append(combobox.itemText(i))
    
    combobox_items.sort()
    expected_items.sort()
    if combobox_items != expected_items:
        logging.error(f'combobox_items: {combobox_items}')
        logging.error(f'expected_items: {expected_items}')
    assert combobox_items == expected_items

# https://pytest-qt.readthedocs.io/en/latest/tutorial.html


def test_add_audio(qtbot):
    # pytest test_dialogs.py -rPP -k test_add_audio

    config_gen = testing_utils.TestConfigGenerator()

    # test 1 - everything setup but no prior setting
    # ----------------------------------------------
    mock_language_tools = config_gen.build_languagetools_instance('default')

    deck_note_type = mock_language_tools.deck_utils.build_deck_note_type(config_gen.deck_id, config_gen.model_id)

    note_id_list = [42, 43]
    add_audio_dialog = dialogs.AddAudioDialog(mock_language_tools, deck_note_type, note_id_list)
    add_audio_dialog.setupUi()

    # do some checks on the from field combo box
    assert_combobox_items_equal(add_audio_dialog.from_field_combobox, ['Chinese', 'English'])
    assert_combobox_items_equal(add_audio_dialog.to_field_combobox, config_gen.all_fields)
    assert add_audio_dialog.voice_label.text() == '<b>' + config_gen.chinese_voice_description + '</b>'

    # test 2 - some defaults already exist
    # ------------------------------------
    mock_language_tools = config_gen.build_languagetools_instance('batch_audio')

    add_audio_dialog = dialogs.AddAudioDialog(mock_language_tools, deck_note_type, note_id_list)
    add_audio_dialog.setupUi()
    assert_combobox_items_equal(add_audio_dialog.from_field_combobox, ['Chinese', 'English'])
    assert_combobox_items_equal(add_audio_dialog.to_field_combobox, config_gen.all_fields)

    # verify that selected fields match expectation
    assert add_audio_dialog.from_field_combobox.currentText() == config_gen.field_chinese
    assert add_audio_dialog.to_field_combobox.currentText() == config_gen.field_sound

    # test 3 - no language mapping done for any field
    # -----------------------------------------------
    mock_language_tools = config_gen.build_languagetools_instance('no_language_mapping')

    # add_audio_dialog = dialogs.AddAudioDialog(mock_language_tools, deck_note_type, note_id_list)
    testcase_instance = unittest.TestCase()
    testcase_instance.assertRaises(errors.LanguageMappingError, dialogs.AddAudioDialog, mock_language_tools, deck_note_type, note_id_list)

    # only uncomment if you want to see the dialog come up
    # add_audio_dialog.exec_()

def test_add_translation_transliteration_no_language_mapping(qtbot):
    # pytest test_dialogs.py -rPP -k test_add_translation_transliteration_no_language_mapping

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('no_language_mapping')
    
    deck_note_type = mock_language_tools.deck_utils.build_deck_note_type(config_gen.deck_id, config_gen.model_id)

    note_id_list = [42, 43]

    testcase_instance = unittest.TestCase()
    
    # translation
    testcase_instance.assertRaises(errors.LanguageMappingError, dialog_batchtransformation.BatchConversionDialog, mock_language_tools, deck_note_type, note_id_list, constants.TransformationType.Translation)

    # transliteration
    testcase_instance.assertRaises(errors.LanguageMappingError, dialog_batchtransformation.BatchConversionDialog, mock_language_tools, deck_note_type, note_id_list, constants.TransformationType.Transliteration)



def test_language_mapping(qtbot):
    # pytest test_dialogs.py -rPP -k test_language_mapping

    # make sure our deck appears
    # --------------------------

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('no_language_mapping')

    mapping_dialog = dialog_languagemapping.prepare_language_mapping_dialogue(mock_language_tools)
    
    # assert deck name, note type, and 3 fields
    deck_frame = mapping_dialog.findChild(PyQt5.QtWidgets.QFrame, f'frame_{config_gen.deck_name}')
    assert deck_frame != None
    deck_name_label = mapping_dialog.findChild(PyQt5.QtWidgets.QLabel, f'deck_name_{config_gen.deck_name}')
    assert deck_name_label.text() == config_gen.deck_name
    note_type_label = mapping_dialog.findChild(PyQt5.QtWidgets.QLabel, f'note_type_name_{config_gen.deck_name}_{config_gen.model_name}')
    assert note_type_label.text() == config_gen.model_name

    # look for labels on all 3 fields
    for field_name in config_gen.all_fields:
        field_label_obj_name = f'field_label_{config_gen.model_name} / {config_gen.deck_name} / {field_name}'
        field_label = mapping_dialog.findChild(PyQt5.QtWidgets.QLabel, field_label_obj_name)
        assert field_label.text() == field_name

    # none of the languages should be set
    for field_name in config_gen.all_fields:
        field_language_obj_name = f'field_language_{config_gen.model_name} / {config_gen.deck_name} / {field_name}'
        field_language = mapping_dialog.findChild(PyQt5.QtWidgets.QComboBox, field_language_obj_name)
        assert field_language != None
        # ensure the "not set" option is selected
        assert field_language.currentText() == 'Not Set'

    # now, set languages manually
    # ---------------------------

    field_language_obj_name = f'field_language_{config_gen.model_name} / {config_gen.deck_name} / {config_gen.field_chinese}'
    field_language_combobox = mapping_dialog.findChild(PyQt5.QtWidgets.QComboBox, field_language_obj_name)
    qtbot.keyClicks(field_language_combobox, 'Chinese')
    field_language_obj_name = f'field_language_{config_gen.model_name} / {config_gen.deck_name} / {config_gen.field_english}'
    field_language_combobox = mapping_dialog.findChild(PyQt5.QtWidgets.QComboBox, field_language_obj_name)
    qtbot.keyClicks(field_language_combobox, 'English')

    apply_button = mapping_dialog.findChild(PyQt5.QtWidgets.QPushButton, 'apply')
    qtbot.mouseClick(apply_button, PyQt5.QtCore.Qt.LeftButton)

    # ensure configuration has been modified
    model_name = config_gen.model_name
    deck_name = config_gen.deck_name
    assert mock_language_tools.anki_utils.written_config[constants.CONFIG_DECK_LANGUAGES][model_name][deck_name][config_gen.field_chinese] == 'zh_cn'
    assert mock_language_tools.anki_utils.written_config[constants.CONFIG_DECK_LANGUAGES][model_name][deck_name][config_gen.field_english] == 'en'

    # run automatic detection
    # -----------------------
    
    mapping_dialog = dialog_languagemapping.prepare_language_mapping_dialogue(mock_language_tools)
    # apply button should be disabled
    apply_button = mapping_dialog.findChild(PyQt5.QtWidgets.QPushButton, 'apply')
    assert apply_button.isEnabled() == False

    autodetect_button = mapping_dialog.findChild(PyQt5.QtWidgets.QPushButton, 'run_autodetect')
    qtbot.mouseClick(autodetect_button, PyQt5.QtCore.Qt.LeftButton)
    
    # assert languages detected
    field_language_obj_name = f'field_language_{config_gen.model_name} / {config_gen.deck_name} / {config_gen.field_chinese}'
    field_language = mapping_dialog.findChild(PyQt5.QtWidgets.QComboBox, field_language_obj_name)
    assert field_language.currentText() == 'Chinese'

    field_language_obj_name = f'field_language_{config_gen.model_name} / {config_gen.deck_name} / {config_gen.field_english}'
    field_language = mapping_dialog.findChild(PyQt5.QtWidgets.QComboBox, field_language_obj_name)
    assert field_language.currentText() == 'English'

    # apply button should be enabled
    assert apply_button.isEnabled() == True

    # now , click the apply button
    qtbot.mouseClick(apply_button, PyQt5.QtCore.Qt.LeftButton)

    # ensure configuration has been modified
    model_name = config_gen.model_name
    deck_name = config_gen.deck_name
    assert mock_language_tools.anki_utils.written_config[constants.CONFIG_DECK_LANGUAGES][model_name][deck_name][config_gen.field_chinese] == 'zh_cn'
    assert mock_language_tools.anki_utils.written_config[constants.CONFIG_DECK_LANGUAGES][model_name][deck_name][config_gen.field_english] == 'en'    

    # mapping_dialog.exec_()

    # show field samples
    # ==================

    # reset this
    mock_language_tools.anki_utils.written_config = None
    mapping_dialog = dialog_languagemapping.prepare_language_mapping_dialogue(mock_language_tools)

    field_samples_button_obj_name = f'field_samples_{config_gen.model_name} / {config_gen.deck_name} / {config_gen.field_english}'
    autodetect_button = mapping_dialog.findChild(PyQt5.QtWidgets.QPushButton, field_samples_button_obj_name)
    qtbot.mouseClick(autodetect_button, PyQt5.QtCore.Qt.LeftButton)

    assert 'old people' in mock_language_tools.anki_utils.info_message_received
    assert 'hello' in mock_language_tools.anki_utils.info_message_received

    field_samples_button_obj_name = f'field_samples_{config_gen.model_name} / {config_gen.deck_name} / {config_gen.field_sound}'
    autodetect_button = mapping_dialog.findChild(PyQt5.QtWidgets.QPushButton, field_samples_button_obj_name)
    qtbot.mouseClick(autodetect_button, PyQt5.QtCore.Qt.LeftButton)    

    assert 'No usable field data found' in mock_language_tools.anki_utils.info_message_received

    # set one language manually
    field_language_obj_name = f'field_language_{config_gen.model_name} / {config_gen.deck_name} / {config_gen.field_chinese}'
    field_language_combobox = mapping_dialog.findChild(PyQt5.QtWidgets.QComboBox, field_language_obj_name)
    qtbot.keyClicks(field_language_combobox, 'Sound')

    # hit cancel
    cancel_button = mapping_dialog.findChild(PyQt5.QtWidgets.QPushButton, 'cancel')
    qtbot.mouseClick(cancel_button, PyQt5.QtCore.Qt.LeftButton)
    # there should not be any config change
    assert mock_language_tools.anki_utils.written_config == None

def test_voice_selection(qtbot):
    # pytest test_dialogs.py -rPP -k test_voice_selection

    # make sure the dialog comes up
    # -----------------------------

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('default')

    voice_list = mock_language_tools.cloud_language_tools.get_tts_voice_list('yoyo')
    voice_selection_dialog = dialog_voiceselection.prepare_voice_selection_dialog(mock_language_tools, voice_list)

    # there should be two languages. English And Chinese
    # for each language, there should be two voices
    # they should both have two samples each

    languages_combobox = voice_selection_dialog.findChild(PyQt5.QtWidgets.QComboBox, 'languages_combobox')
    assert languages_combobox.count() == 2
    assert languages_combobox.itemText(0) == 'Chinese'
    assert languages_combobox.itemText(1) == 'English'

    voices_combobox = voice_selection_dialog.findChild(PyQt5.QtWidgets.QComboBox, 'voices_combobox')
    assert voices_combobox.count() == 2
    assert 'Xiaoxiao' in voices_combobox.itemText(0)
    assert 'Yunyang' in voices_combobox.itemText(1)

    # check samples
    assert voice_selection_dialog.sample_labels[0].text() == '老人家'
    assert voice_selection_dialog.sample_labels[1].text() == '你好'

    # now, select English
    qtbot.keyClicks(languages_combobox, 'English')

    assert voices_combobox.count() == 2
    assert 'Aria' in voices_combobox.itemText(0)
    assert 'Guy' in voices_combobox.itemText(1)

    # check samples
    assert voice_selection_dialog.sample_labels[0].text() == 'old people'
    assert voice_selection_dialog.sample_labels[1].text() == 'hello'

    # pick the Guy voice
    guy_voice = voices_combobox.itemText(1)
    qtbot.keyClicks(voices_combobox, guy_voice)

    # listen to samples
    play_sample_button = voice_selection_dialog.findChild(PyQt5.QtWidgets.QPushButton, f'play_sample_0')
    qtbot.mouseClick(play_sample_button, PyQt5.QtCore.Qt.LeftButton)
    # check that sample has been played
    assert mock_language_tools.anki_utils.played_sound['text'] == 'old people'
    assert 'Guy' in mock_language_tools.anki_utils.played_sound['voice_key']['name']

    apply_button = voice_selection_dialog.findChild(PyQt5.QtWidgets.QPushButton, 'apply')
    qtbot.mouseClick(apply_button, PyQt5.QtCore.Qt.LeftButton)

    assert 'en' in mock_language_tools.anki_utils.written_config[constants.CONFIG_VOICE_SELECTION]
    assert 'Guy' in mock_language_tools.anki_utils.written_config[constants.CONFIG_VOICE_SELECTION]['en']['voice_key']['name']

    # use the written config as the new config
    mock_language_tools.config =  mock_language_tools.anki_utils.written_config

    # open the dialog box again
    # =========================

    voice_selection_dialog = dialog_voiceselection.prepare_voice_selection_dialog(mock_language_tools, voice_list)
    apply_button = voice_selection_dialog.findChild(PyQt5.QtWidgets.QPushButton, 'apply')
    assert apply_button.isEnabled() == False # should be disabled

    # switch language to english
    languages_combobox = voice_selection_dialog.findChild(PyQt5.QtWidgets.QComboBox, 'languages_combobox')
    qtbot.keyClicks(languages_combobox, 'English')

    # choose different voice
    voices_combobox = voice_selection_dialog.findChild(PyQt5.QtWidgets.QComboBox, 'voices_combobox')
    current_index = voices_combobox.currentIndex()
    assert voices_combobox.count() == 2
    assert 'Guy' in voices_combobox.itemText(current_index)  # check current english voice
    voice_wanted = voices_combobox.itemText(0)
    qtbot.keyClicks(voices_combobox, voice_wanted)

    assert apply_button.isEnabled() == True
    qtbot.mouseClick(apply_button, PyQt5.QtCore.Qt.LeftButton)

    assert 'Aria' in mock_language_tools.anki_utils.written_config[constants.CONFIG_VOICE_SELECTION]['en']['voice_key']['name']


    # voice_selection_dialog.exec_()

def test_voice_selection_no_voices(qtbot):
    # pytest test_dialogs.py -rPP -k test_voice_selection_no_voices

    # make sure the dialog comes up
    # -----------------------------

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('get_config_language_no_voices')

    voice_list = mock_language_tools.cloud_language_tools.get_tts_voice_list('yoyo')
    voice_selection_dialog = dialog_voiceselection.prepare_voice_selection_dialog(mock_language_tools, voice_list)

    languages_combobox = voice_selection_dialog.findChild(PyQt5.QtWidgets.QComboBox, 'languages_combobox')
    assert languages_combobox.count() == 3
    assert languages_combobox.itemText(2) == 'Malagasy'

    qtbot.keyClicks(languages_combobox, 'Malagasy')

    # try to play audio
    play_sample_button = voice_selection_dialog.findChild(PyQt5.QtWidgets.QPushButton, f'play_sample_0')
    qtbot.mouseClick(play_sample_button, PyQt5.QtCore.Qt.LeftButton)    

    # should have been a critical messages
    assert mock_language_tools.anki_utils.critical_message_received == 'No voice available for Malagasy'


    # voice_selection_dialog.exec_()

def test_choose_translation(qtbot):
    # pytest test_dialogs.py -rPP -k test_choose_translation

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('default')

    original_text = 'translate this'
    from_language = 'zh_cn'
    to_language = 'en'

    all_translations = {
        'serviceA': 'first translation',
        'serviceB': 'second translation'
    }

    dialog = dialog_choosetranslation.prepare_dialog(mock_language_tools, original_text, from_language, to_language, all_translations)

    assert dialog.original_text_label.text() == original_text
    assert dialog.from_language_label.text() == 'Chinese'
    assert dialog.to_language_label.text() == 'English'

    # first, apply button should be disabled
    assert dialog.apply_button.isEnabled() == False

    # check that services and translations are present
    # services
    service_1 = dialog.findChild(PyQt5.QtWidgets.QLabel, 'service_label_0')
    assert service_1.text() == '<b>serviceA</b>'
    service_2 = dialog.findChild(PyQt5.QtWidgets.QLabel, 'service_label_1')
    assert service_2.text() == '<b>serviceB</b>'
    # translations
    translation_1 = dialog.findChild(PyQt5.QtWidgets.QLabel, 'translation_label_0')
    assert translation_1.text() == 'first translation'
    translation_2 = dialog.findChild(PyQt5.QtWidgets.QLabel, 'translation_label_1')
    assert translation_2.text() == 'second translation'

    # pick second translation
    radio_button = dialog.findChild(PyQt5.QtWidgets.QRadioButton, 'radio_button_1')
    radio_button.click()

    # apply button should be enabled
    assert dialog.apply_button.isEnabled() == True
    qtbot.mouseClick(dialog.apply_button, PyQt5.QtCore.Qt.LeftButton)

    # verify translation retained
    assert dialog.selected_translation == 'second translation'

def test_api_key(qtbot):
    # pytest test_dialogs.py -rPP -k test_api_key

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('default')

    # API key already populated
    # =========================

    dialog = dialog_apikey.prepare_api_key_dialog(mock_language_tools)
    # api key will be verified immediately

    assert mock_language_tools.cloud_language_tools.verify_api_key_called == True
    assert mock_language_tools.cloud_language_tools.verify_api_key_input == 'yoyo'

    assert dialog.applyButton.isEnabled() == True
    qtbot.mouseClick(dialog.applyButton, PyQt5.QtCore.Qt.LeftButton)

    # verify that API key in config is correct
    assert mock_language_tools.anki_utils.written_config['api_key'] == 'yoyo'

    
    # API key empty 
    # =============
    mock_language_tools = config_gen.build_languagetools_instance('noapikey')
    assert mock_language_tools.api_key_checked == False
    dialog = dialog_apikey.prepare_api_key_dialog(mock_language_tools)

    assert mock_language_tools.cloud_language_tools.verify_api_key_called == False
    assert dialog.applyButton.isEnabled() == False

    # type in a fake API key
    mock_language_tools.cloud_language_tools.verify_api_key_is_valid = False
    qtbot.keyClicks(dialog.api_text_input, 'dummykey1')

    assert mock_language_tools.cloud_language_tools.verify_api_key_called == True
    assert mock_language_tools.cloud_language_tools.verify_api_key_input == 'dummykey1'

    assert dialog.applyButton.isEnabled() == False

    assert  dialog.account_info_label.text() == ''
    
    # type in a valid API key
    mock_language_tools.cloud_language_tools.verify_api_key_is_valid = True
    dialog.api_text_input.clear()
    qtbot.keyClicks(dialog.api_text_input, 'validkey1')

    assert mock_language_tools.cloud_language_tools.verify_api_key_called == True
    assert mock_language_tools.cloud_language_tools.verify_api_key_input == 'validkey1'

    assert mock_language_tools.cloud_language_tools.account_info_called == True
    assert mock_language_tools.cloud_language_tools.account_info_api_key == 'validkey1'

    assert  dialog.account_info_label.text() == """<b>type</b>: 250 chars<br/><b>email</b>: no@spam.com"""    

    assert dialog.applyButton.isEnabled() == True

    # click OK
    qtbot.mouseClick(dialog.applyButton, PyQt5.QtCore.Qt.LeftButton)

    # verify that API key in config is correct
    assert mock_language_tools.anki_utils.written_config['api_key'] == 'validkey1'
    assert mock_language_tools.api_key_checked == True

def test_batch_transformation(qtbot):
    # pytest test_dialogs.py -rPP -k test_batch_transformation

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('default')

    deck_note_type = deck_utils.DeckNoteType(config_gen.deck_id, config_gen.deck_name, config_gen.model_id, config_gen.model_name)
    note_id_list = config_gen.get_note_id_list()
    transformation_type = constants.TransformationType.Translation

    dialog = dialog_batchtransformation.prepare_batch_transformation_dialogue(mock_language_tools, deck_note_type, note_id_list, transformation_type)

    # assertions
    # ==========
    assert_combobox_items_equal(dialog.from_combobox, ['Chinese', 'English'])
    assert_combobox_items_equal(dialog.to_combobox, ['Chinese', 'English'])
    assert_combobox_items_equal(dialog.service_combobox, ['Azure'])

    # set from to Chinese
    qtbot.keyClicks(dialog.from_combobox, 'Chinese')
    qtbot.keyClicks(dialog.to_combobox, 'English')

    # load translations button should be enabled
    assert dialog.load_translations_button.isEnabled() == True
    # apply to notes should be disabled
    assert dialog.applyButton.isEnabled() == False
    # cancel button should be enabled
    assert dialog.cancelButton.isEnabled() == True

    # check table model
    # =================

    # headers
    assert dialog.noteTableModel.headerData(0, PyQt5.QtCore.Qt.Horizontal, PyQt5.QtCore.Qt.DisplayRole) == 'Chinese'
    assert dialog.noteTableModel.headerData(1, PyQt5.QtCore.Qt.Horizontal, PyQt5.QtCore.Qt.DisplayRole) == 'English'
    # data - input
    column = 0
    index = dialog.noteTableModel.createIndex(0, column)
    assert dialog.noteTableModel.data(index, PyQt5.QtCore.Qt.DisplayRole) == '老人家'
    index = dialog.noteTableModel.createIndex(1, column) # second row
    assert dialog.noteTableModel.data(index, PyQt5.QtCore.Qt.DisplayRole) == '你好'
    # data - output
    column = 1
    index = dialog.noteTableModel.createIndex(0, column)
    assert dialog.noteTableModel.data(index, PyQt5.QtCore.Qt.DisplayRole) == None
    index = dialog.noteTableModel.createIndex(1, column) # second row
    assert dialog.noteTableModel.data(index, PyQt5.QtCore.Qt.DisplayRole) == None

    # load translations
    # =================
    mock_language_tools.cloud_language_tools.translation_map = {
        '老人家': 'translation 1',
        '你好': 'translation 2'
    }
    qtbot.mouseClick(dialog.load_translations_button, PyQt5.QtCore.Qt.LeftButton)

    # ensure translations are displayed on the table
    # data - output
    column = 1
    index = dialog.noteTableModel.createIndex(0, column)
    assert dialog.noteTableModel.data(index, PyQt5.QtCore.Qt.DisplayRole) == 'translation 1'
    index = dialog.noteTableModel.createIndex(1, column) # second row
    assert dialog.noteTableModel.data(index, PyQt5.QtCore.Qt.DisplayRole) == 'translation 2'
    index = dialog.noteTableModel.createIndex(2, column) # third row
    assert dialog.noteTableModel.data(index, PyQt5.QtCore.Qt.DisplayRole) == None

    # apply button should be enabled now
    assert dialog.applyButton.isEnabled() == True

    # apply to notes
    # ==============
    qtbot.mouseClick(dialog.applyButton, PyQt5.QtCore.Qt.LeftButton)

    # verify effect on notes
    note_1 = config_gen.notes_by_id[config_gen.note_id_1]
    assert note_1.set_values == {'English': 'translation 1'}
    assert note_1.flush_called == True
    note_2 = config_gen.notes_by_id[config_gen.note_id_2]
    assert note_2.set_values == {'English': 'translation 2'}
    assert note_2.flush_called == True    

    note_3 = config_gen.notes_by_id[config_gen.note_id_3]
    assert note_3.set_values == {} # no values set
    assert note_3.flush_called == False


    # dialog.exec_()

def test_batch_transformation_error_handling(qtbot):
    # pytest test_dialogs.py -rPP -k test_batch_transformation_error_handling

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('default')

    deck_note_type = deck_utils.DeckNoteType(config_gen.deck_id, config_gen.deck_name, config_gen.model_id, config_gen.model_name)
    note_id_list = config_gen.get_note_id_list()
    transformation_type = constants.TransformationType.Translation

    dialog = dialog_batchtransformation.prepare_batch_transformation_dialogue(mock_language_tools, deck_note_type, note_id_list, transformation_type)

    # assertions
    # ==========
    assert_combobox_items_equal(dialog.from_combobox, ['Chinese', 'English'])
    assert_combobox_items_equal(dialog.to_combobox, ['Chinese', 'English'])
    assert_combobox_items_equal(dialog.service_combobox, ['Azure'])

    # set from to Chinese
    qtbot.keyClicks(dialog.from_combobox, 'Chinese')
    qtbot.keyClicks(dialog.to_combobox, 'English')

    # load translations button should be enabled
    assert dialog.load_translations_button.isEnabled() == True
    # apply to notes should be disabled
    assert dialog.applyButton.isEnabled() == False
    # cancel button should be enabled
    assert dialog.cancelButton.isEnabled() == True

    # check table model
    # =================

    # headers
    assert dialog.noteTableModel.headerData(0, PyQt5.QtCore.Qt.Horizontal, PyQt5.QtCore.Qt.DisplayRole) == 'Chinese'
    assert dialog.noteTableModel.headerData(1, PyQt5.QtCore.Qt.Horizontal, PyQt5.QtCore.Qt.DisplayRole) == 'English'
    # data - input
    column = 0
    index = dialog.noteTableModel.createIndex(0, column)
    assert dialog.noteTableModel.data(index, PyQt5.QtCore.Qt.DisplayRole) == '老人家'
    index = dialog.noteTableModel.createIndex(1, column) # second row
    assert dialog.noteTableModel.data(index, PyQt5.QtCore.Qt.DisplayRole) == '你好'
    # data - output
    column = 1
    index = dialog.noteTableModel.createIndex(0, column)
    assert dialog.noteTableModel.data(index, PyQt5.QtCore.Qt.DisplayRole) == None
    index = dialog.noteTableModel.createIndex(1, column) # second row
    assert dialog.noteTableModel.data(index, PyQt5.QtCore.Qt.DisplayRole) == None

    # load translations
    # =================
    mock_language_tools.cloud_language_tools.translation_error_map = {'老人家': 'translation error 42'}
    mock_language_tools.cloud_language_tools.translation_map = {
        '你好': 'translation 2'
    }

    qtbot.mouseClick(dialog.load_translations_button, PyQt5.QtCore.Qt.LeftButton)

    # ensure translations are displayed on the table
    # data - output
    column = 1
    index = dialog.noteTableModel.createIndex(0, column)
    assert dialog.noteTableModel.data(index, PyQt5.QtCore.Qt.DisplayRole) == None # should be empty, there was an error
    index = dialog.noteTableModel.createIndex(1, column) # second row
    assert dialog.noteTableModel.data(index, PyQt5.QtCore.Qt.DisplayRole) == 'translation 2'

    # dialog.exec_()

    # # apply button should be enabled now
    assert dialog.applyButton.isEnabled() == True

    # apply to notes
    # ==============
    qtbot.mouseClick(dialog.applyButton, PyQt5.QtCore.Qt.LeftButton)

    # verify error message
    assert 'Could not load translation: translation error 42 (1 times)' in mock_language_tools.anki_utils.critical_message_received

    # # verify effect on notes
    note_1 = config_gen.notes_by_id[config_gen.note_id_1]
    assert note_1.set_values == {}
    assert note_1.flush_called == False
    note_2 = config_gen.notes_by_id[config_gen.note_id_2]
    assert note_2.set_values == {'English': 'translation 2'}
    assert note_2.flush_called == True    

    # dialog.exec_()

def test_dialog_textprocessing(qtbot):
    # pytest test_dialogs.py -rPP -k test_dialog_textprocessing

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('default')

    dialog = dialog_textprocessing.prepare_text_processing_dialog(mock_language_tools)

    # check table model
    # =================
    # headers
    assert dialog.textReplacementTableModel.headerData(0, PyQt5.QtCore.Qt.Horizontal, PyQt5.QtCore.Qt.DisplayRole) == 'Type'
    assert dialog.textReplacementTableModel.headerData(1, PyQt5.QtCore.Qt.Horizontal, PyQt5.QtCore.Qt.DisplayRole) == 'Pattern'
    assert dialog.textReplacementTableModel.headerData(2, PyQt5.QtCore.Qt.Horizontal, PyQt5.QtCore.Qt.DisplayRole) == 'Replacement'
    assert dialog.textReplacementTableModel.headerData(3, PyQt5.QtCore.Qt.Horizontal, PyQt5.QtCore.Qt.DisplayRole) == 'Translation'
    assert dialog.textReplacementTableModel.headerData(4, PyQt5.QtCore.Qt.Horizontal, PyQt5.QtCore.Qt.DisplayRole) == 'Transliteration'
    assert dialog.textReplacementTableModel.headerData(5, PyQt5.QtCore.Qt.Horizontal, PyQt5.QtCore.Qt.DisplayRole) == 'Audio'
    # should have 0 rows
    assert dialog.textReplacementTableModel.rowCount(None) == 0

    # check processing preview
    qtbot.keyClicks(dialog.sample_text_input, 'abdc1234')
    assert dialog.sample_text_transformed_label.text() == '<b>abdc1234</b>'

    # add a text transformation rule
    qtbot.mouseClick(dialog.add_replace_regex_button, PyQt5.QtCore.Qt.LeftButton)
    # enter pattern and replacement
    row = 0
    index_pattern = dialog.textReplacementTableModel.createIndex(row, dialog_textprocessing.COL_INDEX_PATTERN)
    dialog.textReplacementTableModel.setData(index_pattern, '1234', PyQt5.QtCore.Qt.EditRole)
    index_replacement = dialog.textReplacementTableModel.createIndex(row, dialog_textprocessing.COL_INDEX_REPLACEMENT)
    dialog.textReplacementTableModel.setData(index_replacement, '5678', PyQt5.QtCore.Qt.EditRole)

    # verify preview
    assert dialog.sample_text_transformed_label.text() == '<b>abdc5678</b>'

    # add another transformation rule
    qtbot.mouseClick(dialog.add_replace_regex_button, PyQt5.QtCore.Qt.LeftButton)
    # enter pattern and replacement
    row = 1
    index_pattern = dialog.textReplacementTableModel.createIndex(row, dialog_textprocessing.COL_INDEX_PATTERN)
    dialog.textReplacementTableModel.setData(index_pattern, ' / ', PyQt5.QtCore.Qt.EditRole)
    index_replacement = dialog.textReplacementTableModel.createIndex(row, dialog_textprocessing.COL_INDEX_REPLACEMENT)
    dialog.textReplacementTableModel.setData(index_replacement, ' ', PyQt5.QtCore.Qt.EditRole)

    # check processing preview
    dialog.sample_text_input.clear()
    qtbot.keyClicks(dialog.sample_text_input, 'word1 / word2')
    assert dialog.sample_text_transformed_label.text() == '<b>word1 word2</b>'

    # go back to previous preview string
    dialog.sample_text_input.clear()
    qtbot.keyClicks(dialog.sample_text_input, 'abdc1234')
    assert dialog.sample_text_transformed_label.text() == '<b>abdc5678</b>'

    # remove the first rule
    dialog.table_view.selectRow(0)
    index_first_row = dialog.textReplacementTableModel.createIndex(0, dialog_textprocessing.COL_INDEX_PATTERN)
    dialog.table_view.selectionModel().select(index_first_row, PyQt5.QtCore.QItemSelectionModel.Select)
    qtbot.mouseClick(dialog.remove_replace_button, PyQt5.QtCore.Qt.LeftButton)

    # there should only be one row left
    assert dialog.textReplacementTableModel.rowCount(None) == 1

    # check the rule at row 0
    row = 0
    index_pattern = dialog.textReplacementTableModel.createIndex(row, dialog_textprocessing.COL_INDEX_PATTERN)
    assert dialog.textReplacementTableModel.data(index_pattern, PyQt5.QtCore.Qt.DisplayRole) == '\" / \"'
    index_replacement = dialog.textReplacementTableModel.createIndex(row, dialog_textprocessing.COL_INDEX_REPLACEMENT)
    assert dialog.textReplacementTableModel.data(index_replacement, PyQt5.QtCore.Qt.DisplayRole) == '\" \"'
    
    # check the preview
    assert dialog.sample_text_transformed_label.text() == '<b>abdc1234</b>'

    # try a regexp rule
    qtbot.mouseClick(dialog.add_replace_regex_button, PyQt5.QtCore.Qt.LeftButton)
    row = 1
    index_pattern = dialog.textReplacementTableModel.createIndex(row, dialog_textprocessing.COL_INDEX_PATTERN)
    dialog.textReplacementTableModel.setData(index_pattern, '[0-9]+', PyQt5.QtCore.Qt.EditRole)
    index_replacement = dialog.textReplacementTableModel.createIndex(row, dialog_textprocessing.COL_INDEX_REPLACEMENT)
    dialog.textReplacementTableModel.setData(index_replacement, 'number', PyQt5.QtCore.Qt.EditRole)
    # this transformation will only apply to transliteration
    index_translation = dialog.textReplacementTableModel.createIndex(row, 3)
    dialog.textReplacementTableModel.setData(index_translation, PyQt5.QtCore.Qt.Unchecked, PyQt5.QtCore.Qt.CheckStateRole)
    index_transliteration = dialog.textReplacementTableModel.createIndex(row, 4)
    dialog.textReplacementTableModel.setData(index_transliteration, PyQt5.QtCore.Qt.Checked, PyQt5.QtCore.Qt.CheckStateRole)
    index_audio = dialog.textReplacementTableModel.createIndex(row, 5)
    dialog.textReplacementTableModel.setData(index_audio, PyQt5.QtCore.Qt.Unchecked, PyQt5.QtCore.Qt.CheckStateRole)

    # check the preview in different transformation types
    dialog.sample_transformation_type_combo_box.setCurrentText('Transliteration')
    assert dialog.sample_text_transformed_label.text() == '<b>abdcnumber</b>'

    dialog.sample_transformation_type_combo_box.setCurrentText('Translation')
    assert dialog.sample_text_transformed_label.text() == '<b>abdc1234</b>'

    dialog.sample_transformation_type_combo_box.setCurrentText('Audio')
    assert dialog.sample_text_transformed_label.text() == '<b>abdc1234</b>'

    # now, click OK to the dialog
    qtbot.mouseClick(dialog.applyButton, PyQt5.QtCore.Qt.LeftButton)

    # ensure that config has been written
    actual_written_config = mock_language_tools.anki_utils.written_config
    actual_written_config_text_processing = actual_written_config[constants.CONFIG_TEXT_PROCESSING]
    expected_written_config_text_processing = {
        'replacements': 
            [
                {'Audio': True,
                'Transliteration': True,
                'Translation': True,
                'pattern': ' / ',
                'replace': ' ',
                'replace_type': 'regex'},
                {'Audio': False,
                'Transliteration': True,
                'Translation': False,
                'pattern': '[0-9]+',
                'replace': 'number',
                'replace_type': 'regex'},
            ]
    }

    assert actual_written_config_text_processing['replacements'][0] == expected_written_config_text_processing['replacements'][0]
    assert actual_written_config_text_processing['replacements'][1] == expected_written_config_text_processing['replacements'][1]

    # try to generate some translations
    source_text = 'word1 / word2'
    mock_language_tools.cloud_language_tools.translation_map = {
        'word1 word2': 'word3 word4'
    }
    translated_text = mock_language_tools.get_translation(source_text, {'translation_key': 'de to en'})
    assert translated_text == 'word3 word4'

    # try to generate transliteration
    source_text = 'word1 / word2'
    mock_language_tools.cloud_language_tools.transliteration_map = {
        'wordnumber wordnumber': 'correct correct'
    }
    translated_text = mock_language_tools.get_transliteration(source_text, {'translation_key': 'de to en'})
    assert translated_text == 'correct correct'

def test_dialog_textprocessing_simple(qtbot):
    # pytest test_dialogs.py -rPP -k test_dialog_textprocessing_simple

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('default')

    dialog = dialog_textprocessing.prepare_text_processing_dialog(mock_language_tools)

    # check table model
    # =================
    # should have 0 rows
    assert dialog.textReplacementTableModel.rowCount(None) == 0

    # check processing preview
    qtbot.keyClicks(dialog.sample_text_input, 'abdc1234 [9]+')
    assert dialog.sample_text_transformed_label.text() == '<b>abdc1234 [9]+</b>'

    # add a text transformation rule
    qtbot.mouseClick(dialog.add_replace_simple_button, PyQt5.QtCore.Qt.LeftButton)
    # enter pattern and replacement
    row = 0
    index_pattern = dialog.textReplacementTableModel.createIndex(row, dialog_textprocessing.COL_INDEX_PATTERN)
    dialog.textReplacementTableModel.setData(index_pattern, ' [9]+', PyQt5.QtCore.Qt.EditRole) # should not get interpreted as regexp
    index_replacement = dialog.textReplacementTableModel.createIndex(row, dialog_textprocessing.COL_INDEX_REPLACEMENT)
    dialog.textReplacementTableModel.setData(index_replacement, 'rep', PyQt5.QtCore.Qt.EditRole)

    # dialog.exec_()

    # verify preview
    assert dialog.sample_text_transformed_label.text() == '<b>abdc1234rep</b>'

def test_dialog_breakdown_chinese(qtbot):
    # pytest test_dialogs.py -rPP -k test_dialog_breakdown_chinese

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('default')

    source_text = '老人家'

    # the response which should come
    mock_language_tools.cloud_language_tools.breakdown_map = {
        '老人家': [
            {
                'token': '老',
                'lemma': '老',
                'translation': 'old',
                'transliteration': 'lao'
            },
            {
                'token': '人家',
                'lemma': '人家',
                'translation': 'people',
                'transliteration': 'renjia'
            },            
        ]
    }

    deck_note_type = deck_utils.DeckNoteType(config_gen.deck_id, config_gen.deck_name, config_gen.model_id, config_gen.model_name)
    dialog = dialog_breakdown.prepare_dialog(mock_language_tools, source_text, 'zh_cn', None, deck_note_type)

    # wanted languages should be populated
    assert_combobox_items_equal(dialog.target_language_dropdown, [
        'English',
        'Chinese'
    ])
    assert dialog.target_language_dropdown.currentText() == 'Chinese'

    # there should be 1 translation option (Azure)
    assert_combobox_items_equal(dialog.translation_dropdown, ['Azure'])

    # there should be 2 transliteration options
    assert_combobox_items_equal(dialog.transliteration_dropdown, ['pinyin1', 'pinyin2'])

    # there should be 2 tokenization options
    assert_combobox_items_equal(dialog.tokenization_dropdown, ['Chinese (Simplified) (Characters) Spacy',
        'Chinese (Simplified) (Jieba (words)) Spacy'])

    # run breakdown
    qtbot.mouseClick(dialog.load_button, PyQt5.QtCore.Qt.LeftButton)

    # check that result label has been populated
    result_text = dialog.breakdown_result.text()
    result_lines = result_text.split('<br/>')
    assert len(result_lines) == 2


def test_dialog_runrules(qtbot):
    # pytest test_dialogs.py -rPP -k test_dialog_runrules

    config_gen = testing_utils.TestConfigGenerator()
    mock_language_tools = config_gen.build_languagetools_instance('batch_audio_translation_transliteration')

    deck_note_type = deck_utils.DeckNoteType(config_gen.deck_id, config_gen.deck_name, config_gen.model_id, config_gen.model_name)
    note_id_list = config_gen.get_note_id_list()

    # setup maps for translation / transliteration
    mock_language_tools.cloud_language_tools.translation_map = {
        '老人家': 'translation 1',
        '你好': 'translation 2'
    }
    mock_language_tools.cloud_language_tools.transliteration_map = {
        '老人家': 'transliteration 1',
        '你好': 'transliteration 2'
    }

    dialog = dialog_notesettings.RunRulesDialog(mock_language_tools, deck_note_type, note_id_list)
    dialog.setupUi()
    # dialog.exec_()

    # click apply button
    qtbot.mouseClick(dialog.applyButton, PyQt5.QtCore.Qt.LeftButton)

    # ideally we would check things like buttons disabled, progress bar, etc
    # but for now, just check the effect on notes

    # verify effect on notes
    note_1 = config_gen.notes_by_id[config_gen.note_id_1]
    note_1_set_values = note_1.set_values
    assert 'sound:' in note_1_set_values['Sound']
    del note_1_set_values['Sound'] # look at sound separately
    assert note_1_set_values == {'English': 'translation 1',
                                 'Pinyin': 'transliteration 1'}
    assert note_1.flush_called == True
    note_2 = config_gen.notes_by_id[config_gen.note_id_2]
    note_2_set_values = note_2.set_values
    assert 'sound:' in note_2_set_values['Sound']
    del note_2_set_values['Sound']
    assert note_2_set_values == {'English': 'translation 2',
                                 'Pinyin': 'transliteration 2'}
    assert note_2.flush_called == True    

    note_3 = config_gen.notes_by_id[config_gen.note_id_3]
    assert note_3.set_values == {} # no values set
    assert note_3.flush_called == False

    # check action stats
    expected_action_stats = {
        'adding translation to field English': {
            'success': 2, 'error': {'Field is empty': 1}
        }, 
        'adding transliteration to field Pinyin': {
            'success': 2, 'error': {'Field is empty': 1}
        }, 
        'adding audio to field Sound': {
            'success': 2, 'error': {'Field is empty': 1}
        }
    }
    actual_action_stats = dialog.batch_error_manager.action_stats
    logging.info(actual_action_stats)
    assert expected_action_stats == actual_action_stats    
    




