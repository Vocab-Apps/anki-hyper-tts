
import os
import json
import constants
import servicemanager

def test_services_dir():
    current_script_path = os.path.realpath(__file__)
    current_script_dir = os.path.dirname(current_script_path)    
    return os.path.join(current_script_dir, 'test_services')

def test_discover(qtbot):
    # discover available services
    manager = servicemanager.ServiceManager(test_services_dir())
    module_names = manager.discover_services()
    assert module_names == ['service_a', 'service_b']


def test_import(qtbot):
    manager = servicemanager.ServiceManager(test_services_dir(), 'test_services')
    manager.init_services()


def test_full_voice_list(qtbot):
    manager = servicemanager.ServiceManager(test_services_dir(), 'test_services')
    manager.init_services()
    voice_list = manager.full_voice_list()

    # find ServiceA's voice_1
    subset = [voice for voice in voice_list if voice.service.name == 'ServiceA' and voice.gender == constants.Gender.Male]
    assert len(subset) == 1
    servicea_voice_1 = subset[0]
    assert servicea_voice_1.name == 'voice_a_1'
    assert servicea_voice_1.language == constants.AudioLanguage.fr_FR

    subset = [voice for voice in voice_list if voice.service.name == 'ServiceB' and voice.name == 'jane']
    assert len(subset) == 1
    servicea_voice_1 = subset[0]
    assert servicea_voice_1.name == 'jane'
    assert servicea_voice_1.language == constants.AudioLanguage.ja_JP


def test_get_tts_audio(qtbot):
    manager = servicemanager.ServiceManager(test_services_dir(), 'test_services')
    manager.init_services()
    voice_list = manager.full_voice_list()

    # find ServiceA's voice_1
    subset = [voice for voice in voice_list if voice.service.name == 'ServiceA' and voice.gender == constants.Gender.Male]
    assert len(subset) == 1
    servicea_voice_1 = subset[0]

    audio_result = manager.get_tts_audio('test sentence 123', servicea_voice_1)

    audio_result_dict = json.loads(audio_result)

    assert audio_result_dict['source_text'] == 'test sentence 123'
    assert audio_result_dict['language'] == 'fr_FR'
    assert audio_result_dict['voice_key'] == {'name': 'voice_1'}

def test_services_configuration(qtbot):
    manager = servicemanager.ServiceManager(test_services_dir(), 'test_services')
    manager.init_services()    

    service_a_options = manager.service_configuration_options('ServiceA')
    assert service_a_options == {'api_key': str, 'region': ['us', 'europe'], 'delay': int}

    for key, value in service_a_options.items():
        if value == str:
            print(f'{key} is a string')
        elif value == int:
            print(f'{key} is integer')
        elif isinstance(value, list):
            print(f'{key} is list')
