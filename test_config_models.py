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
