import testing_utils

def test_simple(qtbot):
    # create batch configuration
    # ==========================

    batch_config = {
        'mode': 'simple',
        'source_field': 'Chinese',
        'target_field': 'Sound',
        'text_and_sound_tag': False,
        'remove_sound_tag': True,
        'voice': {
            'service': 'ServiceA',
            'voice_key': {
                'name': 'voice_1'
            },
            'options': {}
        }
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
    mock_hypertts.process_batch_audio(note_id_list, batch_config)

    # verify effect on notes
    # ======================
    # target field has the sound tag
    # note.flush() has been called

    note_1 = mock_hypertts.anki_utils.get_note_by_id(config_gen.note_id_1)
    assert 'Sound' in note_1.set_values 
    assert note_1.set_values['Sound'] == '[sound:yoyo.mp3]'