
import os
import constants
import servicemanager


def test_discover(qtbot):
    # discover available services
    current_script_path = os.path.realpath(__file__)
    current_script_dir = os.path.dirname(current_script_path)    
    test_services_dir = os.path.join(current_script_dir, 'test_services')
    manager = servicemanager.ServiceManager(test_services_dir)
    module_names = manager.discover_services()
    assert module_names == ['service_a', 'service_b']
