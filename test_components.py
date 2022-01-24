import PyQt5
import logging
import copy
import component_batch_preview
import config_models
import servicemanager
import testing_utils
import hypertts
import constants
import component_voiceselection
import component_source
import component_target
import component_batch

class EmptyDialog(PyQt5.QtWidgets.QDialog):
    def __init__(self):
        super(PyQt5.QtWidgets.QDialog, self).__init__()
        self.closed = None

    def setupUi(self):
        self.main_layout = PyQt5.QtWidgets.QVBoxLayout(self)

    def getLayout(self):
        return self.main_layout

    def setLayout(self, layout):
        self.main_layout = layout

    def addChildLayout(self, layout):
        self.main_layout.addLayout(layout)
    
    def close(self):
        self.closed = True

class MockModelChangeCallback():
    def __init__(self):
        self.model = None

    def model_updated(self, model):
        logging.info('MockModelChangeCallback.model_updated')
        self.model = copy.deepcopy(model)

class MockBatchPreviewCallback():
    def __init__(self):
        self.sample_text = None
        self.batch_start_called = None
        self.batch_end_called = None

    def sample_selected(self, note_id, text):
        self.note_id = note_id
        self.sample_text = text

    def batch_start(self):
        self.batch_start_called = True

    def batch_end(self):
        self.batch_end_called = True

class MockEditor():
    def __init__(self):
        self.set_note_called = None

    def set_note(self, note):
        self.set_note_called = True

def get_hypertts_instance():
    # return hypertts_instance    
    config_gen = testing_utils.TestConfigGenerator()
    return config_gen.build_hypertts_instance_test_servicemanager('default')


def test_voice_selection_defaults_single(qtbot):
    hypertts_instance = get_hypertts_instance()

    dialog = EmptyDialog()
    dialog.setupUi()

    model_change_callback = MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, model_change_callback.model_updated)
    dialog.addChildLayout(voiceselection.draw())

    # voiceselection.voices_combobox.setCurrentIndex(1) # pick second voice
    expected_output = {
        'voice_selection_mode': 'single',
        'voice': {
            'voice': {
                'gender': 'Male', 
                'language': 'fr_FR',
                'name': 'voice_a_1', 
                'service': 'ServiceA',
                'voice_key': {'name': 'voice_1'}
            },
            'options': {
            }
        }        
    }

    assert voiceselection.serialize() == expected_output

    # dialog.exec_()
    
def test_voice_selection_single_1(qtbot):
    hypertts_instance = get_hypertts_instance()

    dialog = EmptyDialog()
    dialog.setupUi()

    model_change_callback = MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, model_change_callback.model_updated)
    dialog.addChildLayout(voiceselection.draw())

    voiceselection.voices_combobox.setCurrentIndex(1) # pick second voice

    # dialog.exec_()

    expected_output = {
        'voice_selection_mode': 'single',
        'voice': {
            'voice': {
                'gender': 'Female', 
                'language': 'en_US',
                'name': 'voice_a_2', 
                'service': 'ServiceA',
                'voice_key': {'name': 'voice_2'}
            },
            'options': {
            }
        }        
    }
    assert voiceselection.serialize() == expected_output    

    # change options
    speaking_rate_widget = dialog.findChild(PyQt5.QtWidgets.QDoubleSpinBox, "voice_option_speaking_rate")
    speaking_rate_widget.setValue(0.25)

    expected_output = {
        'voice_selection_mode': 'single',
        'voice': {
            'voice': {
                'gender': 'Female', 
                'language': 'en_US',
                'name': 'voice_a_2', 
                'service': 'ServiceA',
                'voice_key': {'name': 'voice_2'}
            },
            'options': {
                'speaking_rate': 0.25
            }
        }        
    }
    assert voiceselection.serialize() == expected_output        

def test_voice_selection_random_1(qtbot):
    hypertts_instance = get_hypertts_instance()

    dialog = EmptyDialog()
    dialog.setupUi()

    model_change_callback = MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, model_change_callback.model_updated)
    dialog.addChildLayout(voiceselection.draw())

    # choose random mode
    # qtbot.mouseClick(voiceselection.radio_button_random, PyQt5.QtCore.Qt.LeftButton)
    voiceselection.radio_button_random.setChecked(True)

    # pick second voice and add it
    voiceselection.voices_combobox.setCurrentIndex(1) # pick second voice
    qtbot.mouseClick(voiceselection.add_voice_button, PyQt5.QtCore.Qt.LeftButton)

    # pick third voice and add it
    voiceselection.voices_combobox.setCurrentIndex(2) # pick second voice
    qtbot.mouseClick(voiceselection.add_voice_button, PyQt5.QtCore.Qt.LeftButton)    

    expected_output = {
        'voice_selection_mode': 'random',
        'voice_list': [
            {
                'voice': {
                    'gender': 'Female', 
                    'language': 'en_US',
                    'name': 'voice_a_2', 
                    'service': 'ServiceA',
                    'voice_key': {'name': 'voice_2'}
                },
                'options': {
                },
                'weight': 1
            },
            {
                'voice': {
                    'gender': 'Female', 
                    'language': 'ja_JP',
                    'name': 'voice_a_3', 
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
    hypertts_instance = get_hypertts_instance()

    dialog = EmptyDialog()
    dialog.setupUi()

    model_change_callback = MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, model_change_callback.model_updated)
    dialog.addChildLayout(voiceselection.draw())

    # choose random mode
    # qtbot.mouseClick(voiceselection.radio_button_random, PyQt5.QtCore.Qt.LeftButton)
    voiceselection.radio_button_random.setChecked(True)

    # pick second voice and add it
    voiceselection.voices_combobox.setCurrentIndex(1) # pick second voice
    qtbot.mouseClick(voiceselection.add_voice_button, PyQt5.QtCore.Qt.LeftButton)

    # pick third voice and add it
    voiceselection.voices_combobox.setCurrentIndex(2) # pick second voice
    qtbot.mouseClick(voiceselection.add_voice_button, PyQt5.QtCore.Qt.LeftButton)    

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
    hypertts_instance = get_hypertts_instance()

    dialog = EmptyDialog()
    dialog.setupUi()

    model_change_callback = MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, model_change_callback.model_updated)
    dialog.addChildLayout(voiceselection.draw())

    # choose random mode
    # qtbot.mouseClick(voiceselection.radio_button_random, PyQt5.QtCore.Qt.LeftButton)
    voiceselection.radio_button_random.setChecked(True)

    # pick second voice and add it
    voiceselection.voices_combobox.setCurrentIndex(1) # pick second voice
    qtbot.mouseClick(voiceselection.add_voice_button, PyQt5.QtCore.Qt.LeftButton)

    # pick third voice and add it
    voiceselection.voices_combobox.setCurrentIndex(2) # pick second voice
    qtbot.mouseClick(voiceselection.add_voice_button, PyQt5.QtCore.Qt.LeftButton)    

    # check model change callback
    assert model_change_callback.model.selection_mode == constants.VoiceSelectionMode.random
    assert len(model_change_callback.model.get_voice_list()) == 2

    # now remove one of the voices
    logging.info('removing voice_row_1')
    remove_voice_button = dialog.findChild(PyQt5.QtWidgets.QPushButton, 'remove_voice_row_1')
    qtbot.mouseClick(remove_voice_button, PyQt5.QtCore.Qt.LeftButton)

    # check model change callback
    assert model_change_callback.model.selection_mode == constants.VoiceSelectionMode.random
    assert len(model_change_callback.model.get_voice_list()) == 1



def test_voice_selection_random_2(qtbot):
    hypertts_instance = get_hypertts_instance()

    dialog = EmptyDialog()
    dialog.setupUi()

    model_change_callback = MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, model_change_callback.model_updated)
    dialog.addChildLayout(voiceselection.draw())

    # choose random mode
    voiceselection.radio_button_random.setChecked(True)

    # add the first voice twice, but with different options
    voiceselection.voices_combobox.setCurrentIndex(0)
    qtbot.mouseClick(voiceselection.add_voice_button, PyQt5.QtCore.Qt.LeftButton)

    # change options
    speaking_rate_widget = dialog.findChild(PyQt5.QtWidgets.QDoubleSpinBox, "voice_option_speaking_rate")
    speaking_rate_widget.setValue(0.25)    

    # add again
    qtbot.mouseClick(voiceselection.add_voice_button, PyQt5.QtCore.Qt.LeftButton)

    # build expected voice selection model
    expected_model = config_models.VoiceSelectionRandom()
    voice = [x for x in hypertts_instance.service_manager.full_voice_list() if x.service.name == 'ServiceA' and x.name == 'voice_a_1'][0]

    expected_model.add_voice(config_models.VoiceWithOptionsRandom(voice, {}))
    expected_model.add_voice(config_models.VoiceWithOptionsRandom(voice, {'speaking_rate': 0.25}))    

    assert voiceselection.voice_selection_model.serialize() == expected_model.serialize()


def test_voice_selection_priority_1(qtbot):
    hypertts_instance = get_hypertts_instance()

    dialog = EmptyDialog()
    dialog.setupUi()

    model_change_callback = MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, model_change_callback.model_updated)
    dialog.addChildLayout(voiceselection.draw())

    # choose random mode
    # qtbot.mouseClick(voiceselection.radio_button_random, PyQt5.QtCore.Qt.LeftButton)
    voiceselection.radio_button_priority.setChecked(True)

    # dialog.exec_()

    # pick second voice and add it
    voiceselection.voices_combobox.setCurrentIndex(1) # pick second voice
    qtbot.mouseClick(voiceselection.add_voice_button, PyQt5.QtCore.Qt.LeftButton)

    # pick third voice and add it
    voiceselection.voices_combobox.setCurrentIndex(2) # pick second voice
    qtbot.mouseClick(voiceselection.add_voice_button, PyQt5.QtCore.Qt.LeftButton)    

    expected_model = config_models.VoiceSelectionPriority()
    voice_2 = [x for x in hypertts_instance.service_manager.full_voice_list() if x.service.name == 'ServiceA' and x.name == 'voice_a_2'][0]
    voice_3 = [x for x in hypertts_instance.service_manager.full_voice_list() if x.service.name == 'ServiceA' and x.name == 'voice_a_3'][0]

    expected_model.add_voice(config_models.VoiceWithOptionsPriority(voice_2, {}))
    expected_model.add_voice(config_models.VoiceWithOptionsPriority(voice_3, {}))

    assert voiceselection.voice_selection_model.serialize() == expected_model.serialize()

    # dialog.exec_()


def test_voice_selection_filters(qtbot):
    manager = servicemanager.ServiceManager(testing_utils.get_test_services_dir(), 'test_services')
    manager.init_services()
    manager.get_service('ServiceA').set_enabled(True)
    manager.get_service('ServiceB').set_enabled(True)
    anki_utils = testing_utils.MockAnkiUtils({})

    hypertts_instance = hypertts.HyperTTS(anki_utils, manager)

    dialog = EmptyDialog()
    dialog.setupUi()

    model_change_callback = MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, model_change_callback.model_updated)
    dialog.addChildLayout(voiceselection.draw())

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
        assert voice.language.lang == constants.Language.ja

    # reset filters
    qtbot.mouseClick(voiceselection.reset_filters_button, PyQt5.QtCore.Qt.LeftButton)

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
    qtbot.mouseClick(voiceselection.reset_filters_button, PyQt5.QtCore.Qt.LeftButton)
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
        assert voice.language.lang == constants.Language.ja

    # reset filters again
    qtbot.mouseClick(voiceselection.reset_filters_button, PyQt5.QtCore.Qt.LeftButton)    

    # select random mode and add some voices
    # ======================================


    # dialog.exec_()

def test_voice_selection_samples(qtbot):
    hypertts_instance = get_hypertts_instance()

    dialog = EmptyDialog()
    dialog.setupUi()

    model_change_callback = MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, model_change_callback.model_updated)
    dialog.addChildLayout(voiceselection.draw())

    # simulate selection from the preview grid
    voiceselection.sample_text_selected('Bonjour')

    qtbot.mouseClick(voiceselection.play_sample_button, PyQt5.QtCore.Qt.LeftButton)

    assert hypertts_instance.anki_utils.played_sound == {
        'source_text': 'Bonjour',
        'voice': {
            'gender': 'Male', 
            'language': 'fr_FR', 
            'name': 'voice_a_1', 
            'service': 'ServiceA',
            'voice_key': {'name': 'voice_1'}
        },
        'options': {}
    }

    # dialog.exec_()

def test_voice_selection_load_model(qtbot):
    hypertts_instance = get_hypertts_instance()

    dialog = EmptyDialog()
    dialog.setupUi()

    model_change_callback = MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, model_change_callback.model_updated)
    dialog.addChildLayout(voiceselection.draw())

    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_2 = [x for x in voice_list if x.name == 'voice_a_2'][0]
    voice_a_3 = [x for x in voice_list if x.name == 'voice_a_3'][0]

    # single voice
    # ============

    model = config_models.VoiceSelectionSingle()
    model.voice = config_models.VoiceWithOptions(voice_a_2, {'speaking_rate': 3.5})

    voiceselection.load_model(model)

    assert voiceselection.radio_button_single.isChecked()
    assert voiceselection.voices_combobox.currentText() == str(voice_a_2)


    speaking_rate_widget = voiceselection.voice_options_widgets['voice_option_speaking_rate']
    assert speaking_rate_widget != None
    assert speaking_rate_widget.value() == 3.5

    # random
    # =======

    model = config_models.VoiceSelectionRandom()
    model.add_voice(config_models.VoiceWithOptionsRandom(voice_a_2, {'speaking_rate': 2.5}))
    model.add_voice(config_models.VoiceWithOptionsRandom(voice_a_3, {}))

    voiceselection.load_model(model)
    
    assert voiceselection.radio_button_random.isChecked()

    assert voiceselection.voice_list_grid_layout.itemAt(0).widget().text() == str(voice_a_2) + ' (speaking_rate: 2.5)'
    assert voiceselection.voice_list_grid_layout.itemAt(3).widget().text() == str(voice_a_3)

    # priority
    # ========

    model = config_models.VoiceSelectionPriority()
    model.add_voice(config_models.VoiceWithOptionsPriority(voice_a_2, {'speaking_rate': 2.5}))
    model.add_voice(config_models.VoiceWithOptionsPriority(voice_a_3, {}))

    voiceselection.load_model(model)
    
    assert voiceselection.radio_button_priority.isChecked()

    assert voiceselection.voice_list_grid_layout.itemAt(0).widget().text() == str(voice_a_2) + ' (speaking_rate: 2.5)'
    assert voiceselection.voice_list_grid_layout.itemAt(4).widget().text() == str(voice_a_3)    

    # dialog.exec_()





def test_batch_source_1(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')    

    dialog = EmptyDialog()
    dialog.setupUi()

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]

    model_change_callback = MockModelChangeCallback()
    field_list = hypertts_instance.get_all_fields_from_notes(note_id_list)
    batch_source = component_source.BatchSource(hypertts_instance, field_list, model_change_callback.model_updated)
    dialog.addChildLayout(batch_source.draw())

    # the field selected should be "Chinese"
    expected_source_model = config_models.BatchSource()
    expected_source_model.mode = constants.BatchMode.simple
    expected_source_model.source_field = 'Chinese'

    assert batch_source.batch_source_model.serialize() == expected_source_model.serialize()

    # select another field, 'English'
    batch_source.source_field_combobox.setCurrentText('English')
    expected_source_model.source_field = 'English'

    assert batch_source.batch_source_model.serialize() == expected_source_model.serialize()

    # select template mode
    batch_source.batch_mode_combobox.setCurrentText('template')

    # enter template format
    qtbot.keyClicks(batch_source.simple_template_input, '{Chinese}')

    expected_source_model = config_models.BatchSource()
    expected_source_model.mode = constants.BatchMode.template
    expected_source_model.source_template = '{Chinese}'
    expected_source_model.template_format_version = constants.TemplateFormatVersion.v1

    assert batch_source.batch_source_model.serialize() == expected_source_model.serialize()

    # load model tests
    # ================
    # the field selected should be "Chinese"
    model = config_models.BatchSource()
    model.mode = constants.BatchMode.simple
    model.source_field = 'English'

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

    # dialog.exec_()

def test_target(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')    

    dialog = EmptyDialog()
    dialog.setupUi()

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]

    model_change_callback = MockModelChangeCallback()
    field_list = hypertts_instance.get_all_fields_from_notes(note_id_list)
    batch_target = component_target.BatchTarget(hypertts_instance, field_list, model_change_callback.model_updated)
    dialog.addChildLayout(batch_target.draw())

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

    model = config_models.BatchTarget('Chinese', False, True)
    batch_target.load_model(model)

    assert batch_target.target_field_combobox.currentText() == 'Chinese'
    assert batch_target.radio_button_sound_only.isChecked() == True
    assert batch_target.radio_button_remove_sound.isChecked() == True

    model = config_models.BatchTarget('Pinyin', True, True)
    batch_target.load_model(model)

    assert batch_target.target_field_combobox.currentText() == 'Pinyin'
    assert batch_target.radio_button_sound_only.isChecked() == False
    assert batch_target.radio_button_remove_sound.isChecked() == True

def test_batch_preview(qtbot):

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    # configure delay on service A
    # hypertts_instance.service_manager.get_service('ServiceA').configure({'delay': 1.0})

    dialog = EmptyDialog()
    dialog.setupUi()

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    

    voice_list = hypertts_instance.service_manager.full_voice_list()

    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    voice_selection = config_models.VoiceSelectionSingle()
    voice_selection.set_voice(config_models.VoiceWithOptions(voice_a_1, {}))

    batch_config = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('Chinese')
    target = config_models.BatchTarget('Sound', False, True)

    batch_config.set_source(source)
    batch_config.set_target(target)
    batch_config.set_voice_selection(voice_selection)    

    batch_preview_callback = MockBatchPreviewCallback()
    batch_preview = component_batch_preview.BatchPreview(hypertts_instance, note_id_list, 
        batch_preview_callback.sample_selected,
        batch_preview_callback.batch_start,
        batch_preview_callback.batch_end)
    batch_preview.load_model(batch_config)
    dialog.addChildLayout(batch_preview.draw())

    # dialog.exec_()
    # return 


def test_batch_dialog(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    dialog = EmptyDialog()
    dialog.setupUi()

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    

    # test saving of config
    # =====================

    batch = component_batch.ComponentBatch(hypertts_instance, dialog)
    batch.configure_browser(note_id_list)
    batch.draw(dialog.getLayout())

    # select a source field and target field
    batch.source.source_field_combobox.setCurrentText('English')
    batch.target.target_field_combobox.setCurrentText('Sound')

    # set profile name
    batch.profile_name_combobox.setCurrentText('batch profile 1')

    # save button should be enabled
    assert batch.profile_save_button.isEnabled() == True
    # save
    qtbot.mouseClick(batch.profile_save_button, PyQt5.QtCore.Qt.LeftButton)
    # should be disabled after saving
    assert batch.profile_save_button.isEnabled() == False
    assert batch.profile_load_button.isEnabled() == False
    assert batch.profile_save_button.text() == 'Preset Saved'

    print(hypertts_instance.anki_utils.written_config)
    assert 'batch profile 1' in hypertts_instance.anki_utils.written_config[constants.CONFIG_BATCH_CONFIG]

    # try to deserialize that config, it should have the English field selected
    deserialized_model = hypertts_instance.load_batch_config('batch profile 1')
    assert deserialized_model.source.source_field == 'English'
    assert deserialized_model.target.target_field == 'Sound'

    # test loading of config
    # ======================

    dialog = EmptyDialog()
    dialog.setupUi()
    batch = component_batch.ComponentBatch(hypertts_instance, dialog)
    batch.configure_browser(note_id_list)
    batch.draw(dialog.getLayout())    

    # dialog.exec_()

    assert batch.profile_load_button.isEnabled() == False
    # select preset
    batch.profile_name_combobox.setCurrentText('batch profile 1')
    # should be enabled now
    assert batch.profile_load_button.isEnabled() == True
    assert batch.profile_load_button.text() == 'Load'

    # open
    qtbot.mouseClick(batch.profile_load_button, PyQt5.QtCore.Qt.LeftButton)

    # button should go back to disabled
    assert batch.profile_load_button.isEnabled() == False
    assert batch.profile_save_button.isEnabled() == False
    assert batch.profile_load_button.text() == 'Preset Loaded'

    # assertions on GUI
    assert batch.source.source_field_combobox.currentText() == 'English'
    assert batch.target.target_field_combobox.currentText() == 'Sound'
    
    # dialog.exec_()

    # play sound preview
    # ==================

    # select second row
    index_second_row = batch.preview.batch_preview_table_model.createIndex(1, 0)
    batch.preview.table_view.selectionModel().select(index_second_row, PyQt5.QtCore.QItemSelectionModel.Select)
    # press preview button
    qtbot.mouseClick(batch.preview_sound_button, PyQt5.QtCore.Qt.LeftButton)
    # dialog.exec_()

    assert hypertts_instance.anki_utils.played_sound == {
        'source_text': 'hello',
        'voice': {
            'gender': 'Male', 
            'language': 'fr_FR', 
            'name': 'voice_a_1', 
            'service': 'ServiceA',
            'voice_key': {'name': 'voice_1'}
        },
        'options': {}
    }    

    # load audio
    # ==========

    batch.source.source_field_combobox.setCurrentText('Chinese')
    qtbot.mouseClick(batch.apply_button, PyQt5.QtCore.Qt.LeftButton)

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


    # dialog.exec_()


def test_batch_dialog_editor(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')

    dialog = EmptyDialog()
    dialog.setupUi()

    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]    
    note = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)

    mock_editor = MockEditor()

    batch = component_batch.ComponentBatch(hypertts_instance, dialog)
    batch.configure_editor(note, mock_editor, False)
    batch.draw(dialog.getLayout())

    # test sound preview
    # ==================
    qtbot.mouseClick(batch.preview_sound_button, PyQt5.QtCore.Qt.LeftButton)
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
    # dialog.exec_()
    
    # set target field
    batch.target.target_field_combobox.setCurrentText('Sound')

    # apply not note
    qtbot.mouseClick(batch.apply_button, PyQt5.QtCore.Qt.LeftButton)

    sound_tag = note.set_values['Sound']
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == '老人家'

    assert mock_editor.set_note_called == True

    assert dialog.closed == True

