import os

import aqt.qt

from test_utils import testing_utils
from test_utils import gui_testing_utils

from hypertts_addon import component_config_backup
from hypertts_addon import component_preferences
from hypertts_addon import config_backup
from hypertts_addon import constants
from hypertts_addon import logging_utils

from tests.test_config_backup import get_populated_config

logger = logging_utils.get_test_child_logger(__name__)


def build_hypertts_instance(config=None):
    config_gen = testing_utils.TestConfigGenerator()
    if config == None:
        config = get_populated_config()
    return config_gen.build_hypertts_instance_test_servicemanager_config(config)


def build_component(hypertts_instance):
    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    component = component_config_backup.ConfigBackup(hypertts_instance, dialog)
    dialog.addChildWidget(component.draw())
    return component, dialog


def test_config_backup_table(qtbot):
    # pytest tests/test_component_config_backup.py -k test_config_backup_table
    hypertts_instance = build_hypertts_instance()

    # a second backup, with an extra preset
    hypertts_instance.anki_utils.tick_time()
    hypertts_instance.config[constants.CONFIG_PRESETS]['uuid_3'] = {'uuid': 'uuid_3', 'name': 'preset 3'}
    hypertts_instance.persist_config()

    component, dialog = build_component(hypertts_instance)

    # the backups are listed, most recent first
    assert component.table.rowCount() == 2
    assert component.table.item(0, component_config_backup.COLUMN_INDEX_PRESETS).text() == '3'
    assert component.table.item(1, component_config_backup.COLUMN_INDEX_PRESETS).text() == '2'
    assert component.table.item(0, component_config_backup.COLUMN_INDEX_STATUS).text() == 'OK'
    assert component.table.item(0, component_config_backup.COLUMN_INDEX_RULES).text() == '1'
    assert component.table.item(0, component_config_backup.COLUMN_INDEX_SERVICES).text() == '1'
    assert component.table.item(0, component_config_backup.COLUMN_INDEX_API_KEY).text() == 'yes'
    assert component.table.item(0, component_config_backup.COLUMN_INDEX_SAVED).text() != ''

    # the current configuration is described at the top
    assert '3 presets' in component.current_config_label.text()
    assert 'API key set' in component.current_config_label.text()

    # and the backup directory is shown so users can find the files
    assert component.backup_manager.get_backup_dir() in component.backup_directory_label.text()

    # nothing is selected yet, so restoring is not possible
    assert component.restore_button.isEnabled() == False


def test_config_backup_table_empty(qtbot):
    # pytest tests/test_component_config_backup.py -k test_config_backup_table_empty
    # a fresh install: no backups, empty configuration
    hypertts_instance = build_hypertts_instance({})
    component, dialog = build_component(hypertts_instance)

    assert component.table.rowCount() == 0
    assert component.restore_button.isEnabled() == False
    assert 'empty' in component.current_config_label.text()


def test_config_backup_corrupted_backup(qtbot):
    # pytest tests/test_component_config_backup.py -k test_config_backup_corrupted_backup
    hypertts_instance = build_hypertts_instance()
    backup_manager = hypertts_instance.config_backup_manager

    # a corrupted backup file, more recent than the good one
    corrupted_filename = f'{constants.CONFIG_BACKUP_FILE_PREFIX}29991231_235959.json'
    with open(os.path.join(backup_manager.get_backup_dir(), corrupted_filename), 'w') as f:
        f.write('{"config": {"presets"')

    component, dialog = build_component(hypertts_instance)

    assert component.table.rowCount() == 2
    assert 'Corrupted' in component.table.item(0, component_config_backup.COLUMN_INDEX_STATUS).text()

    # the corrupted backup cannot be restored
    component.table.selectRow(0)
    assert component.restore_button.isEnabled() == False

    # the valid one can
    component.table.selectRow(1)
    assert component.restore_button.isEnabled() == True


def test_config_backup_restore(qtbot):
    # pytest tests/test_component_config_backup.py -k test_config_backup_restore
    hypertts_instance = build_hypertts_instance()
    component, dialog = build_component(hypertts_instance)

    # the user loses their configuration
    hypertts_instance.anki_utils.tick_time()
    hypertts_instance.config = {}
    assert hypertts_instance.persist_config() == False
    hypertts_instance.anki_utils.written_config = None

    # they open the backups tab and restore the most recent backup
    hypertts_instance.anki_utils.tick_time()
    component.refresh()
    assert 'empty' in component.current_config_label.text()
    assert component.table.rowCount() == 1
    component.table.selectRow(0)
    assert component.restore_button.isEnabled() == True

    hypertts_instance.anki_utils.ask_user_bool_response = True
    qtbot.mouseClick(component.restore_button, aqt.qt.Qt.MouseButton.LeftButton)

    # the configuration is back
    assert len(hypertts_instance.config[constants.CONFIG_PRESETS]) == 2
    assert len(hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS]) == 2
    assert hypertts_instance.anki_utils.info_message_received == constants.GUI_TEXT_CONFIG_BACKUP_RESTART
    # and the table was refreshed
    assert '2 presets' in component.current_config_label.text()


def test_config_backup_restore_cancelled(qtbot):
    # pytest tests/test_component_config_backup.py -k test_config_backup_restore_cancelled
    hypertts_instance = build_hypertts_instance()
    component, dialog = build_component(hypertts_instance)

    hypertts_instance.anki_utils.tick_time()
    hypertts_instance.config = {}
    hypertts_instance.persist_config()
    hypertts_instance.anki_utils.written_config = None
    component.refresh()

    component.table.selectRow(0)
    hypertts_instance.anki_utils.ask_user_bool_response = False
    qtbot.mouseClick(component.restore_button, aqt.qt.Qt.MouseButton.LeftButton)

    # nothing was restored
    assert hypertts_instance.config == {}
    assert hypertts_instance.anki_utils.written_config == None


def test_config_backup_preferences_tab(qtbot):
    # pytest tests/test_component_config_backup.py -k test_config_backup_preferences_tab
    # the configuration backups are reachable from the preferences dialog
    hypertts_instance = build_hypertts_instance()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    preferences = component_preferences.ComponentPreferences(hypertts_instance, dialog)
    preferences.load_model(hypertts_instance.get_preferences())
    preferences.draw(dialog.getLayout())

    tab_names = [preferences.tabs.tabText(index) for index in range(preferences.tabs.count())]
    assert 'Configuration Backups' in tab_names
    assert preferences.config_backup.table.rowCount() == 1

    # drawing the tab must not enable the apply button
    assert preferences.save_button.isEnabled() == False


def test_config_backup_manual(qtbot):
    # HYPERTTS_CONFIG_BACKUP_DIALOG_DEBUG=yes pytest tests/test_component_config_backup.py -k test_config_backup_manual -s -rPP
    hypertts_instance = build_hypertts_instance()

    # a few backups to look at
    for i in range(3):
        hypertts_instance.anki_utils.tick_time()
        hypertts_instance.config[constants.CONFIG_PRESETS][f'uuid_extra_{i}'] = {
            'uuid': f'uuid_extra_{i}', 'name': f'preset extra {i}'}
        hypertts_instance.persist_config()

    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    preferences = component_preferences.ComponentPreferences(hypertts_instance, dialog)
    preferences.load_model(hypertts_instance.get_preferences())
    preferences.draw(dialog.getLayout())
    preferences.tabs.setCurrentIndex(
        [preferences.tabs.tabText(index) for index in range(preferences.tabs.count())].index(
            'Configuration Backups'))

    if os.environ.get('HYPERTTS_CONFIG_BACKUP_DIALOG_DEBUG', 'no') == 'yes':
        dialog.exec()
