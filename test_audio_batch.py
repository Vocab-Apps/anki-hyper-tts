import testing_utils
import constants

class mock_progress_bar():
    def __init__(self):
        self.iteration = 0

    def callback_fn(self, iteration):
        self.iteration = iteration


def test_simple_1(qtbot):
    # create batch configuration
    # ==========================

    batch_config = {
        'mode': 'simple',
        'source_field': 'Chinese',
        'target_field': 'Sound',
        'text_and_sound_tag': False,
        'remove_sound_tag': True,
        'voices': [{
            'service': 'ServiceA',
            'voice_key': {
                'name': 'voice_1'
            },
            'options': {}
        }]
    }
    
    # create hypertts instance
    # ========================

    config_gen = testing_utils.TestConfigGenerator()
    mock_hypertts = config_gen.build_hypertts_instance('default')

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = mock_hypertts.process_batch_audio(note_id_list, batch_config, progress_bar.callback_fn)

    # check progress bar
    assert progress_bar.iteration == 2

    # verify effect on notes
    # ======================
    # target field has the sound tag
    # note.flush() has been called

    # check note 1

    note_1 = mock_hypertts.anki_utils.get_note_by_id(config_gen.note_id_1)
    assert 'Sound' in note_1.set_values 

    sound_tag = note_1.set_values['Sound']
    audio_full_path = mock_hypertts.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = mock_hypertts.service_manager.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == '老人家'
    assert audio_data['voice'] == batch_config['voices'][0]
    assert note_1.flush_called == True

    note_2 = mock_hypertts.anki_utils.get_note_by_id(config_gen.note_id_2)
    assert 'Sound' in note_2.set_values 

    sound_tag = note_2.set_values['Sound']
    audio_full_path = mock_hypertts.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = mock_hypertts.service_manager.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == '你好'
    assert audio_data['voice'] == batch_config['voices'][0]
    assert note_2.flush_called == True    

    # verify batch error manager stats
    assert batch_error_manager.action_stats['success'] == 2
    assert len(batch_error_manager.action_stats['error']) == 0

def test_simple_error_handling(qtbot):
    # include one empty field 

    # create batch configuration
    # ==========================

    batch_config = {
        'mode': 'simple',
        'source_field': 'Chinese',
        'target_field': 'Sound',
        'text_and_sound_tag': False,
        'remove_sound_tag': True,
        'voices': [{
            'service': 'ServiceA',
            'voice_key': {
                'name': 'voice_1'
            },
            'options': {}
        }]
    }
    
    # create hypertts instance
    # ========================

    config_gen = testing_utils.TestConfigGenerator()
    mock_hypertts = config_gen.build_hypertts_instance('default')

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1, config_gen.note_id_2, config_gen.note_id_3]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = mock_hypertts.process_batch_audio(note_id_list, batch_config, progress_bar.callback_fn)

    # check progress bar
    assert progress_bar.iteration == 3

    # verify batch error manager stats
    assert batch_error_manager.action_stats['success'] == 2
    assert len(batch_error_manager.action_stats['error']) == 1
    assert batch_error_manager.action_stats['error']['Source text is empty'] == 1

def test_simple_append(qtbot):
    # create batch configuration
    # ==========================

    batch_config = {
        'mode': constants.BatchMode.simple.name,
        'source_field': 'Chinese',
        'target_field': 'Chinese',
        constants.CONFIG_BATCH_TEXT_AND_SOUND_TAG: True,
        'remove_sound_tag': True,
        'voices': [{
            'service': 'ServiceA',
            'voice_key': {
                'name': 'voice_1'
            },
            'options': {}
        }]
    }
    
    # create hypertts instance
    # ========================

    config_gen = testing_utils.TestConfigGenerator()
    mock_hypertts = config_gen.build_hypertts_instance('default')

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1, config_gen.note_id_2]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = mock_hypertts.process_batch_audio(note_id_list, batch_config, progress_bar.callback_fn)

    # check progress bar
    assert progress_bar.iteration == 2

    # verify effect on notes
    # ======================
    # target field has the sound tag
    # note.flush() has been called

    # check note 1

    note_1 = mock_hypertts.anki_utils.get_note_by_id(config_gen.note_id_1)
    assert 'Chinese' in note_1.set_values 

    text_and_sound_tag = note_1.set_values['Chinese']
    assert '老人家 ' in text_and_sound_tag
    audio_full_path = mock_hypertts.anki_utils.extract_sound_tag_audio_full_path(text_and_sound_tag)
    audio_data = mock_hypertts.service_manager.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == '老人家'
    assert audio_data['voice'] == batch_config['voices'][0]
    assert note_1.flush_called == True

def test_random_voices(qtbot):
    batch_config = {
        'mode': 'simple',
        'source_field': 'Chinese',
        'target_field': 'Sound',
        'text_and_sound_tag': False,
        'remove_sound_tag': True,
        'voices': [
            {
                'service': 'ServiceA',
                'voice_key': {
                    'name': 'voice_1'
                },
                'options': {}
            },
            {
                'service': 'ServiceA',
                'voice_key': {
                    'name': 'voice_2'
                },
                'options': {}
            },
            {
                'service': 'ServiceA',
                'voice_key': {
                    'name': 'voice_3'
                },
                'options': {}
            }
        ]
    }
    
    # create hypertts instance
    # ========================

    config_gen = testing_utils.TestConfigGenerator()
    mock_hypertts = config_gen.build_hypertts_instance('default')

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_1]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = mock_hypertts.process_batch_audio(note_id_list, batch_config, progress_bar.callback_fn)

    note_1 = mock_hypertts.anki_utils.get_note_by_id(config_gen.note_id_1)
    assert 'Sound' in note_1.set_values 

    sound_tag = note_1.set_values['Sound']
    audio_full_path = mock_hypertts.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = mock_hypertts.service_manager.extract_mock_tts_audio(audio_full_path)

    assert audio_data['voice'] == batch_config['voices'][0] or batch_config['voices'][1] or batch_config['voices'][2]

def test_template(qtbot):
    # create batch configuration
    # ==========================

    batch_config = {
        'mode': constants.BatchMode.advanced_template.name,
        'source_template': """
word = template_fields['Word']
article = template_fields['Article']
result = f"{article} {word}"
""",
        'source_field': 'Chinese',
        'target_field': 'Sound',
        'text_and_sound_tag': False,
        'remove_sound_tag': True,
        'voices': [{
            'service': 'ServiceA',
            'voice_key': {
                'name': 'voice_1'
            },
            'options': {}
        }]
    }
    
    # create hypertts instance
    # ========================

    config_gen = testing_utils.TestConfigGenerator()
    mock_hypertts = config_gen.build_hypertts_instance('default')

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_german_1]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = mock_hypertts.process_batch_audio(note_id_list, batch_config, progress_bar.callback_fn)

    note_1 = mock_hypertts.anki_utils.get_note_by_id(config_gen.note_id_german_1)
    assert 'Sound' in note_1.set_values 

    sound_tag = note_1.set_values['Sound']
    audio_full_path = mock_hypertts.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = mock_hypertts.service_manager.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == 'Das Hund'
    assert audio_data['voice'] == batch_config['voices'][0]
    assert note_1.flush_called == True    


def test_template_imports(qtbot):
    # create batch configuration
    # ==========================

    batch_config = {
        'mode': constants.BatchMode.advanced_template.name,
        'source_template': """
import re
word = template_fields['Word']
article = template_fields['Article']
article = re.sub('Das', 'das', article)
result = f"{article} {word}"
""",
        'source_field': 'Chinese',
        'target_field': 'Sound',
        'text_and_sound_tag': False,
        'remove_sound_tag': True,
        'voices': [{
            'service': 'ServiceA',
            'voice_key': {
                'name': 'voice_1'
            },
            'options': {}
        }]
    }
    
    # create hypertts instance
    # ========================

    config_gen = testing_utils.TestConfigGenerator()
    mock_hypertts = config_gen.build_hypertts_instance('default')

    # create list of notes
    # ====================
    note_id_list = [config_gen.note_id_german_1]

    # run batch add audio (simple mode)
    # =================================
    progress_bar = mock_progress_bar()
    batch_error_manager = mock_hypertts.process_batch_audio(note_id_list, batch_config, progress_bar.callback_fn)

    note_1 = mock_hypertts.anki_utils.get_note_by_id(config_gen.note_id_german_1)
    assert 'Sound' in note_1.set_values 

    sound_tag = note_1.set_values['Sound']
    audio_full_path = mock_hypertts.anki_utils.extract_sound_tag_audio_full_path(sound_tag)
    audio_data = mock_hypertts.service_manager.extract_mock_tts_audio(audio_full_path)

    assert audio_data['source_text'] == 'das Hund' # lowercase d
    assert audio_data['voice'] == batch_config['voices'][0]
    assert note_1.flush_called == True        

