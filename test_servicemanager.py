
import os
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
    manager.import_services()


def test_full_voice_list(qtbot):
    manager = servicemanager.ServiceManager(test_services_dir(), 'test_services')
    manager.import_services()
    voice_list = manager.full_voice_list()

    # find ServiceA's voice_1
    subset = [voice for voice in voice_list if voice.service == 'ServiceA' and voice.gender == constants.Gender.male]
    assert len(subset) == 1
    servicea_voice_1 = subset[0]
    assert servicea_voice_1.name == 'voice_a_1'
    assert servicea_voice_1.language == constants.Language.fr

    subset = [voice for voice in voice_list if voice.service == 'ServiceB' and voice.name == 'jane']
    assert len(subset) == 1
    servicea_voice_1 = subset[0]
    assert servicea_voice_1.name == 'jane'
    assert servicea_voice_1.language == constants.Language.ja