import os
import servicemanager

def services_dir():
    current_script_path = os.path.realpath(__file__)
    current_script_dir = os.path.dirname(current_script_path)    
    return os.path.join(current_script_dir, 'services')

def test_google():
    manager = servicemanager.ServiceManager(services_dir(), 'services')
    manager.init_services()
    voice_list = manager.full_voice_list()
    # print(voice_list)
    assert len(voice_list) > 0

