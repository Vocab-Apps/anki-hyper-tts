import os

import pytest

from test_utils import testing_utils

from hypertts_addon import config_models
from hypertts_addon import constants
from hypertts_addon import servicemanager


def build_service_manager(extensions_directory):
    return servicemanager.ServiceManager(
        testing_utils.get_test_services_dir(),
        f'{constants.DIR_HYPERTTS_ADDON}.test_services',
        True,
        testing_utils.MockCloudLanguageTools(),
        extensions_directory=extensions_directory)


# directory resolution
# ====================

def test_resolve_extensions_directory_repository_root():
    # the user is asked for the repository root, which contains a services/ subdirectory
    extensions_dir = testing_utils.get_test_extensions_dir()
    resolved = servicemanager.resolve_extensions_services_directory(extensions_dir)
    assert resolved == os.path.join(extensions_dir, constants.DIR_SERVICES)

def test_resolve_extensions_directory_services_subdirectory():
    # be lenient: users frequently point at the services/ subdirectory itself
    services_dir = os.path.join(testing_utils.get_test_extensions_dir(), constants.DIR_SERVICES)
    assert servicemanager.resolve_extensions_services_directory(services_dir) == services_dir

def test_resolve_extensions_directory_not_configured():
    assert servicemanager.resolve_extensions_services_directory(None) == None
    assert servicemanager.resolve_extensions_services_directory('') == None
    assert servicemanager.resolve_extensions_services_directory('   ') == None

def test_resolve_extensions_directory_no_services(tmp_path):
    # a directory which exists but holds no service files
    assert servicemanager.resolve_extensions_services_directory(str(tmp_path)) == None

def test_resolve_extensions_directory_does_not_exist():
    assert servicemanager.resolve_extensions_services_directory('/does/not/exist/hypertts') == None

def test_find_service_files():
    services_dir = os.path.join(testing_utils.get_test_extensions_dir(), constants.DIR_SERVICES)
    filenames = [os.path.basename(path) for path in servicemanager.find_service_files(services_dir)]
    # the data file sitting next to the services must not be picked up
    assert filenames == ['service_ext_broken.py', 'service_ext_datafile.py', 'service_ext_working.py']


# loading
# =======

def test_extension_services_are_loaded():
    manager = build_service_manager(testing_utils.get_test_extensions_dir())
    manager.init_services()

    assert manager.service_exists('ExtensionServiceWorking')
    assert 'ExtensionServiceWorking' in manager.extension_service_names
    # built-in services are still there
    assert manager.service_exists('ServiceA')
    assert 'ServiceA' not in manager.extension_service_names

def test_extension_voices_show_up_in_voice_list():
    manager = build_service_manager(testing_utils.get_test_extensions_dir())
    manager.init_services()

    configuration = config_models.Configuration()
    configuration.set_service_enabled('ExtensionServiceWorking', True)
    manager.configure(configuration)

    voice_names = [voice.name for voice in manager.full_voice_list()]
    assert 'extension_voice_1' in voice_names

def test_extensions_disabled():
    # extensions_directory of None means the feature is turned off
    manager = build_service_manager(None)
    manager.init_services()

    assert not manager.service_exists('ExtensionServiceWorking')
    assert manager.extension_service_names == set()
    assert manager.extension_load_errors == []

def test_extensions_directory_missing():
    # the checkout was moved or deleted. HyperTTS must still start up
    manager = build_service_manager('/does/not/exist/hypertts')
    manager.init_services()

    assert manager.service_exists('ServiceA')
    assert not manager.service_exists('ExtensionServiceWorking')
    assert len(manager.extension_load_errors) == 1

def test_broken_extension_does_not_prevent_startup():
    # service_ext_broken.py raises ImportError at import time
    manager = build_service_manager(testing_utils.get_test_extensions_dir())
    manager.init_services()

    assert len(manager.extension_load_errors) == 1
    load_error = manager.extension_load_errors[0]
    assert load_error.source == 'service_ext_broken.py'
    assert 'this_module_does_not_exist_hypertts_test' in load_error.message

    # the other extension services, and the built-in services, loaded fine
    assert manager.service_exists('ExtensionServiceWorking')
    assert manager.service_exists('ExtensionServiceDataFile')
    assert manager.service_exists('ServiceA')

def test_extension_can_load_data_file_next_to_it():
    # extension services resolve data files through __file__ (see service_openrouter.py in the
    # anki-hyper-tts-extensions repository), so __file__ has to be set correctly
    manager = build_service_manager(testing_utils.get_test_extensions_dir())
    manager.init_services()

    service = manager.get_service('ExtensionServiceDataFile')
    voice_names = [voice.name for voice in service.voice_list()]
    assert voice_names == ['datafile_voice_1', 'datafile_voice_2']

def test_extension_name_collision_builtin_wins():
    # the collision fixture declares a class named ServiceA, same as a built-in test service
    manager = build_service_manager(testing_utils.get_test_extensions_collision_dir())
    manager.init_services()

    # the built-in ServiceA is the one which is registered
    assert manager.get_service('ServiceA').__module__ == f'{constants.DIR_HYPERTTS_ADDON}.test_services.service_a'
    assert 'ServiceA' not in manager.extension_service_names

    assert len(manager.extension_load_errors) == 1
    assert manager.extension_load_errors[0].source == 'ServiceA'

def test_extension_services_do_not_leak_between_managers():
    # ServiceBase subclasses are process-wide, so a manager without extensions must not pick up
    # services which were imported by another manager
    manager_with_extensions = build_service_manager(testing_utils.get_test_extensions_dir())
    manager_with_extensions.init_services()
    assert manager_with_extensions.service_exists('ExtensionServiceWorking')

    manager_without_extensions = build_service_manager(None)
    manager_without_extensions.init_services()
    assert not manager_without_extensions.service_exists('ExtensionServiceWorking')


# configuration is never pruned
# =============================

def test_extension_service_config_survives_missing_directory():
    # regression: save_configuration calls remove_non_existent_services, which used to delete the
    # configuration (including API keys) of any service which wasn't currently loaded
    manager = build_service_manager(testing_utils.get_test_extensions_dir())
    manager.init_services()

    configuration = config_models.Configuration()
    configuration.set_service_enabled('ExtensionServiceWorking', True)
    configuration.set_service_configuration_key('ExtensionServiceWorking', 'api_key', 'my_api_key')
    configuration = manager.remove_non_existent_services(configuration)
    assert 'ExtensionServiceWorking' in configuration.extension_service_names

    # anki restarts with the extensions directory gone
    manager_without_extensions = build_service_manager(None)
    manager_without_extensions.init_services()
    configuration = manager_without_extensions.remove_non_existent_services(configuration)

    assert configuration.get_service_enabled_map()['ExtensionServiceWorking'] == True
    assert configuration.get_service_config()['ExtensionServiceWorking']['api_key'] == 'my_api_key'

def test_unknown_services_are_still_pruned():
    # services which were never extensions still get cleaned up
    manager = build_service_manager(None)
    manager.init_services()

    configuration = config_models.Configuration()
    configuration.set_service_enabled('ServiceA', True)
    configuration.set_service_enabled('ServiceDoesNotExist', True)
    configuration.set_service_configuration_key('ServiceDoesNotExist', 'api_key', 'key')
    configuration = manager.remove_non_existent_services(configuration)

    assert 'ServiceA' in configuration.get_service_enabled_map()
    assert 'ServiceDoesNotExist' not in configuration.get_service_enabled_map()
    assert 'ServiceDoesNotExist' not in configuration.get_service_config()


# preferences model
# =================

def test_preferences_extensions_round_trip():
    preferences = config_models.Preferences()
    preferences.extensions.enabled = True
    preferences.extensions.extensions_directory = '/home/user/anki-hyper-tts-extensions'

    serialized = config_models.serialize_preferences(preferences)
    assert serialized[constants.CONFIG_EXTENSIONS] == {
        'enabled': True,
        'extensions_directory': '/home/user/anki-hyper-tts-extensions'
    }

    deserialized = config_models.deserialize_preferences(serialized)
    assert deserialized.extensions.enabled == True
    assert deserialized.extensions.extensions_directory == '/home/user/anki-hyper-tts-extensions'

def test_preferences_without_extensions_still_deserializes():
    # configs written by previous HyperTTS versions don't have the extensions key
    preferences = config_models.deserialize_preferences({
        'keyboard_shortcuts': {'shortcut_editor_add_audio': 'Ctrl+H'}
    })
    assert preferences.extensions.enabled == False
    assert preferences.extensions.extensions_directory == None
