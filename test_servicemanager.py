
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


