import hypertts
import testing_utils
import constants
import config_models
import logging
import pprint

class mock_progress_bar():
    def __init__(self):
        self.iteration = 0

    def callback_fn(self, iteration):
        self.iteration = iteration


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

    batch.set_source(source)
    batch.set_target(target)
    batch.set_voice_selection(single)

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = hypertts_instance.process_batch_audio(note_id_list, batch, progress_bar.callback_fn)

    if len(batch_error_manager.action_stats['error']) > 0:
        logging.error(batch_error_manager.action_stats)

    # check progress bar
    assert progress_bar.iteration == 2

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
    assert batch_error_manager.action_stats['success'] == 2
    assert len(batch_error_manager.action_stats['error']) == 0

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

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1, config_gen.note_id_2, config_gen.note_id_3]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = hypertts_instance.process_batch_audio(note_id_list, batch, progress_bar.callback_fn)

    # check progress bar
    assert progress_bar.iteration == 3

    # verify batch error manager stats
    assert batch_error_manager.action_stats['success'] == 2
    assert len(batch_error_manager.action_stats['error']) == 1
    assert batch_error_manager.action_stats['error']['Source text is empty'] == 1

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


    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = hypertts_instance.process_batch_audio(note_id_list, batch, progress_bar.callback_fn)

    # check progress bar
    assert progress_bar.iteration == 2

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

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = hypertts_instance.process_batch_audio(note_id_list, batch, progress_bar.callback_fn)

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

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_german_1]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = hypertts_instance.process_batch_audio(note_id_list, batch, progress_bar.callback_fn)

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

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_german_1]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = hypertts_instance.process_batch_audio(note_id_list, batch, progress_bar.callback_fn)

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

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_german_1]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = hypertts_instance.process_batch_audio(note_id_list, batch, progress_bar.callback_fn)

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

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = hypertts_instance.process_batch_audio(note_id_list, batch, progress_bar.callback_fn)

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

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = hypertts_instance.process_batch_audio(note_id_list, batch, progress_bar.callback_fn)

    note_1 = hypertts_instance.anki_utils.get_note_by_id(config_gen.note_id_1)
    assert 'Sound' not in note_1.set_values 

    # make sure we got a AudioNotFoundError in the batch error manager
    assert batch_error_manager.action_stats['success'] == 0
    assert len(batch_error_manager.action_stats['error']) == 1
    assert batch_error_manager.action_stats['error']['Audio not found in any voices for [老人家]'] == 1
