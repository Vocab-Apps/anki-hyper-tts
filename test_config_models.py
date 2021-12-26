import constants
import logging
import servicemanager
import testing_utils
import config_models


def test_voice_selection(qtbot):
    # test the models around voice selection
    # =======================================

    manager = servicemanager.ServiceManager(testing_utils.get_test_services_dir(), 'test_services')
    manager.init_services()
    manager.get_service('ServiceA').set_enabled(True)
    manager.get_service('ServiceB').set_enabled(True)
    voice_list = manager.full_voice_list()    


    voice_a_1 = [x for x in voice_list if x.name == 'voice_a_1'][0]
    voice_jane = [x for x in voice_list if x.name == 'jane'][0]

    # single voice mode
    # =================

    single = config_models.VoiceSelectionSingle()
    single.set_voice(config_models.VoiceWithOptions(voice_a_1, {'speed': 42}))

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
                'speed': 42
            }
        }
    }
    assert single.serialize() == expected_output

    # random voice mode
    # =================

    random = config_models.VoiceSelectionRandom()
    random.add_voice(config_models.VoiceWithOptionsRandom(voice_a_1, {'speed': 43}))
    random.add_voice(config_models.VoiceWithOptionsRandom(voice_jane, {}))

    expected_output = {
        'voice_selection_mode': 'random',
        'voice_list': [
            {
                'voice': {
                    'gender': 'Male', 
                    'language': 'fr_FR', 
                    'name': 'voice_a_1', 
                    'service': 'ServiceA',
                    'voice_key': {'name': 'voice_1'}
                },
                'options': {
                    'speed': 43
                }
            },
            {
                'voice': {
                    'gender': 'Male', 
                    'language': 'ja_JP', 
                    'name': 'jane', 
                    'service': 'ServiceB',
                    'voice_key': {'voice_id': 'jane'}
                },
                'options': {
                }
            },            
        ]
    }
    assert random.serialize() == expected_output
