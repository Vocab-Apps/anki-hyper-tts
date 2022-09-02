import sys
import re
import datetime
import hypertts
import testing_utils
import constants
import languages
import config_models
import batch_status


logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_test_child_logger(__name__)

class mock_progress_bar():
    def __init__(self):
        self.iteration = 0

    def callback_fn(self, iteration):
        self.iteration = iteration


class MockBatchStatusListener():
    def __init__(self, anki_utils):
        self.anki_utils = anki_utils
        self.callbacks_received = {}
        self.current_row = None

        self.batch_started = None
        self.batch_ended = None

    def batch_start(self):
        self.batch_started = True

    def batch_end(self, completed):
        self.batch_ended = True

    def batch_change(self, note_id, row, total_count, start_time, current_time):
        if note_id not in self.callbacks_received:
            self.anki_utils.tick_time()
        self.callbacks_received[note_id] = True
        self.current_row = row
        self.total_count = total_count
        self.start_time = start_time
        self.current_time = current_time

def test_simple_1(qtbot):
    # create batch configuration
    # ==========================

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 42}))    

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('Chinese')
    target = config_models.BatchTarget('Sound', False, True)
    text_processing = config_models.TextProcessing()

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)
    batch.set_text_processing(text_processing)

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]

    # run batch add audio (simple mode)
    # =================================

    start_time = datetime.datetime.now()
    completion_time = start_time + datetime.timedelta(seconds = 2) # two notes, so 2 seconds later
    hypertts_instance.anki_utils.current_time = start_time

    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    assert listener.current_row == 1
    assert listener.callbacks_received[config_gen.note_id_1] == True
    assert listener.callbacks_received[config_gen.note_id_2] == True
    assert listener.batch_started == True
    assert listener.batch_ended == True
    assert listener.start_time == start_time
    assert listener.current_time == completion_time

    # undo handling
    # =============
    assert hypertts_instance.anki_utils.undo_started == True
    assert hypertts_instance.anki_utils.undo_finished == True

    # verify effect on notes
    # ======================
    # target field has the sound tag
    # note.flush() has been called

    # check note 1

    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    assert 'Sound' in note_1.set_values 

    sound_tag = note_1.set_values['Sound']
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == '老人家'
    # pprint.pprint(audio_data)
    assert audio_data['voice']['voice_key'] == {'name': 'voice_1'}
    assert note_1.flush_called == True

    note_2 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_2)
    assert 'Sound' in note_2.set_values 

    sound_tag = note_2.set_values['Sound']
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == '你好'
    assert audio_data['voice']['voice_key'] == {'name': 'voice_1'}
    assert note_2.flush_called == True    

    # verify batch error manager stats
    assert batch_status_obj[0].sound_file != None
    assert batch_status_obj[1].sound_file != None

def test_simple_text_processing(qtbot):
    # create batch configuration
    # ==========================

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 42}))    

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('English')
    target = config_models.BatchTarget('Sound', False, True)
    text_processing = config_models.TextProcessing()
    rule = config_models.TextReplacementRule(constants.TextReplacementRuleType.Simple)
    rule.source = 'hello'
    rule.target = 'goodbye'
    text_processing.add_text_replacement_rule(rule)

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)
    batch.set_text_processing(text_processing)

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_2]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    note_2 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_2)
    assert 'Sound' in note_2.set_values 

    sound_tag = note_2.set_values['Sound']
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == 'goodbye'


def test_simple_error_handling(qtbot):
    # include one empty field 

    # create batch configuration
    # ==========================

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 42}))    

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('Chinese')
    target = config_models.BatchTarget('Sound', False, True)

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)
    batch.set_text_processing(config_models.TextProcessing())

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1, config_gen.note_id_2, config_gen.note_id_3]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)    
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    # check progress bar
    assert listener.current_row == 2

    # verify batch error manager stats
    # verify per-note status
    assert batch_status_obj[0].sound_file != None
    assert batch_status_obj[1].sound_file != None
    assert str(batch_status_obj[2].error) == 'Source text is empty'

def test_simple_error_handling_nonexistent_target_field(qtbot):
    # target field non existent

    # create batch configuration
    # ==========================

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 42}))    

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('Chinese')
    target = config_models.BatchTarget('Audio', False, True)

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)
    batch.set_text_processing(config_models.TextProcessing())

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)    
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    # check progress bar
    assert listener.current_row == 0

    # verify batch error manager stats
    # verify per-note status
    assert str(batch_status_obj[0].error) == 'Target Field <b>Audio</b> not found'

def test_simple_error_handling_nonexistent_source_field(qtbot):
    # target field non existent

    # create batch configuration
    # ==========================

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 42}))    

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('French')
    target = config_models.BatchTarget('Sound', False, True)

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)
    batch.set_text_processing(config_models.TextProcessing())

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)    
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    # check progress bar
    assert listener.current_row == 0

    # verify batch error manager stats
    # verify per-note status
    assert str(batch_status_obj[0].error) == 'Source Field <b>French</b> not found'    

def test_simple_error_handling_not_found(qtbot):
    # the voice responds with not found

    # create batch configuration
    # ==========================

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_b_notfound = [x for x in voice_list if x.name == 'notfound'][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_b_notfound, {}))

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('Chinese')
    target = config_models.BatchTarget('Sound', False, True)

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)
    batch.set_text_processing(config_models.TextProcessing())

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)    
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    # check progress bar
    assert listener.current_row == 1

    # verify batch error manager stats
    # verify per-note status
    assert batch_status_obj[0].sound_file == None
    assert str(batch_status_obj[0].error) == 'Audio not found for [老人家] (voice: Japanese, Male, notfound, ServiceB)'



def test_simple_append(qtbot):
    # create batch configuration
    # ==========================

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {}))    

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('Chinese')
    target = config_models.BatchTarget('Chinese', True, True)

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)
    batch.set_text_processing(config_models.TextProcessing())


    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    # check progress bar
    assert listener.current_row == 1

    # verify effect on notes
    # ======================
    # target field has the sound tag
    # note.flush() has been called

    # check note 1

    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    assert 'Chinese' in note_1.set_values 

    text_and_sound_tag = note_1.set_values['Chinese']
    assert '老人家 ' in text_and_sound_tag
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(text_and_sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == '老人家'
    assert audio_data['voice']['name'] == 'voice_a_1'
    assert note_1.flush_called == True

def test_sound_tag_only_keep_other_sound_tags(qtbot):
    # sound tags only, but append, do not remove other sound tags

    # create batch configuration
    # ==========================

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {}))    

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('Chinese')
    target = config_models.BatchTarget('Sound', 
        False,  # sound tag only
        False)  # do not remove other sound tags

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)
    batch.set_text_processing(config_models.TextProcessing())


    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_4]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    # check progress bar
    assert listener.current_row == 0

    # verify effect on notes
    # ======================
    # target field has the sound tag
    # note.flush() has been called

    # check note 1

    note_4 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_4)
    assert 'Sound' in note_4.set_values 

    two_audio_tags = note_4.set_values['Sound']
    assert '[sound:blabla.mp3] [sound:' in two_audio_tags
    assert note_4.flush_called == True

def test_clear_sound_field_previous_content(qtbot):
    # pytest test_audio_batch.py -k test_clear_sound_field_previous_content
    # there is some existing content in the sound field which should be cleared

    # create batch configuration
    # ==========================

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {}))    

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('Chinese')
    target = config_models.BatchTarget('Sound', 
        False,  # sound tag only
        True)  # do not remove other sound tags

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)
    batch.set_text_processing(config_models.TextProcessing())

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_5]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    # verify effect on notes
    # ======================

    note_5 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_5)
    assert 'Sound' in note_5.set_values 

    sound_tag = note_5.set_values['Sound']
    logger.debug(f'sound_tag: [{sound_tag}]')
    assert re.match(r'\[sound:[^]]+\]', sound_tag) != None

    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == '大使馆'
    assert audio_data['voice']['name'] == 'voice_a_1'
    assert note_5.flush_called == True


def test_simple_same_field_source_target(qtbot):
    # create batch configuration
    # ==========================

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {}))    

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('Chinese')
    target = config_models.BatchTarget('Chinese', True, True)

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)
    batch.set_text_processing(config_models.TextProcessing())


    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    # check progress bar
    assert listener.current_row == 1

    # verify effect on notes
    # ======================
    # target field has the sound tag
    # note.flush() has been called

    # check note 1

    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    assert 'Chinese' in note_1.set_values 

    text_and_sound_tag = note_1.set_values['Chinese']
    assert '老人家 ' in text_and_sound_tag
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(text_and_sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == '老人家'
    assert audio_data['voice']['name'] == 'voice_a_1'
    assert note_1.flush_called == True

def test_simple_sound_only_append(qtbot):
    # create batch configuration
    # ==========================

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {}))    

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('Chinese')
    target = config_models.BatchTarget('Sound', True, False)

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)
    batch.set_text_processing(config_models.TextProcessing())


    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_4]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    # check progress bar
    assert listener.current_row == 0

    # verify effect on notes
    # ======================

    note_4 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_4)
    assert 'Sound' in note_4.set_values
    assert '[sound:blabla.mp3] [sound:' in note_4.set_values['Sound'] 


def test_random_voices(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    voice_a_2 = [x for x in voice_list if x.name == 'voice_a_2'][0]
    voice_a_3 = [x for x in voice_list if x.name == 'voice_a_3'][0]
    random = config_models.VoiceSelectionRandom()
    random.add_voice(config_models.VoiceWithOptionsRandom(voice_a_1, {}))
    random.add_voice(config_models.VoiceWithOptionsRandom(voice_a_2, {}))
    random.add_voice(config_models.VoiceWithOptionsRandom(voice_a_3, {}))

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('Chinese')
    target = config_models.BatchTarget('Sound', False, True)

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(random)
    batch.set_text_processing(config_models.TextProcessing())

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    assert 'Sound' in note_1.set_values 

    sound_tag = note_1.set_values['Sound']
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['voice']['name'] == 'voice_a_1' or 'voice_a_2' or 'voice_a_2'

def test_simple_template(qtbot):
    # create batch configuration
    # ==========================

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 42}))    

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceTemplate(constants.BatchMode.template, """{Article} {Word}""", constants.TemplateFormatVersion.v1)
    target = config_models.BatchTarget('Sound', False, True)

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)
    batch.set_text_processing(config_models.TextProcessing())

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_german_1]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_german_1)
    assert 'Sound' in note_1.set_values 

    sound_tag = note_1.set_values['Sound']
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == 'Das Hund'
    assert audio_data['voice']['name'] == 'voice_a_1'
    assert note_1.flush_called == True    


def test_advanced_template(qtbot):
    # create batch configuration
    # ==========================

    source_template = """
word = template_fields['Word']
article = template_fields['Article']
result = f"{article} {word}"
"""

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 42}))    

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceTemplate(constants.BatchMode.advanced_template, source_template, constants.TemplateFormatVersion.v1)
    target = config_models.BatchTarget('Sound', False, True)

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)    
    batch.set_text_processing(config_models.TextProcessing())

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_german_1]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_german_1)
    assert 'Sound' in note_1.set_values 

    sound_tag = note_1.set_values['Sound']
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == 'Das Hund'
    assert audio_data['voice']['name'] == 'voice_a_1'
    assert note_1.flush_called == True    


def test_advanced_template_imports(qtbot):
    # create batch configuration
    # ==========================

    source_template = """
import re
word = template_fields['Word']
article = template_fields['Article']
article = re.sub('Das', 'das', article)
result = f"{article} {word}"
"""

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 42}))    

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceTemplate(constants.BatchMode.advanced_template, source_template, constants.TemplateFormatVersion.v1)
    target = config_models.BatchTarget('Sound', False, True)

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)    
    batch.set_text_processing(config_models.TextProcessing())

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_german_1]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_german_1)
    assert 'Sound' in note_1.set_values 

    sound_tag = note_1.set_values['Sound']
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == 'das Hund' # lowercase d
    assert audio_data['voice']['name'] == 'voice_a_1'
    assert note_1.flush_called == True        


def test_priority_voices_success(qtbot):
    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_1 = [x for x in voice_list if x.name == 'notfound'][0] # special voice in serviceB
    voice_2 = [x for x in voice_list if x.name == 'voice_a_3'][0]
    priority = config_models.VoiceSelectionPriority()
    priority.add_voice(config_models.VoiceWithOptionsPriority(voice_1, {}))
    priority.add_voice(config_models.VoiceWithOptionsPriority(voice_2, {}))

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('Chinese')
    target = config_models.BatchTarget('Sound', False, True)

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(priority)
    batch.set_text_processing(config_models.TextProcessing())

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    assert 'Sound' in note_1.set_values 

    sound_tag = note_1.set_values['Sound']
    audio_full_path = hypertts_instance.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = hypertts_instance.anki_utils.extract_mock_tts_audio(audio_full_path)

    # should always fallback to the second voice
    assert audio_data['voice']['name'] == 'voice_a_3'


def test_priority_voices_not_found(qtbot):

    config_gen = testing_utils.TestConfigGenerator()
    hypertts_instance = config_gen.build_hypertts_instance_test_servicemanager('default')
        
    # build voice selection model
    voice_list = hypertts_instance.service_manager.full_voice_list()
    voice_1 = [x for x in voice_list if x.name == 'notfound'][0] # special voice in serviceB
    priority = config_models.VoiceSelectionPriority()
    priority.add_voice(config_models.VoiceWithOptionsPriority(voice_1, {}))
    priority.add_voice(config_models.VoiceWithOptionsPriority(voice_1, {}))

    batch = config_models.BatchConfig()
    source = config_models.BatchSourceSimple('Chinese')
    target = config_models.BatchTarget('Sound', False, True)

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(priority)
    batch.set_text_processing(config_models.TextProcessing())

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1]

    # run batch add audio (simple mode)
    # =================================
    listener = MockBatchStatusListener(hypertts_instance.anki_utils)
    batch_status_obj = batch_status.BatchStatus(hypertts_instance.anki_utils, note_id_list, listener)
    hypertts_instance.process_batch_audio(note_id_list, batch, batch_status_obj)

    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    assert 'Sound' not in note_1.set_values 

    # make sure we got a AudioNotFoundError in the batch error manager
    assert str(batch_status_obj[0].error) == 'Audio not found in any voices for [老人家]'
