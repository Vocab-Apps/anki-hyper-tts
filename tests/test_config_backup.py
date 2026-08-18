import copy
import json
import os
import unittest

from test_utils import testing_utils

from hypertts_addon import config_backup
from hypertts_addon import config_models
from hypertts_addon import constants
from hypertts_addon import errors
from hypertts_addon import logging_utils

logger = logging_utils.get_test_child_logger(__name__)


def get_populated_config():
    """a configuration which looks like a real user's configuration"""
    return {
        constants.CONFIG_SCHEMA: constants.CONFIG_SCHEMA_VERSION,
        constants.CONFIG_PRESETS: {
            'uuid_1': {'uuid': 'uuid_1', 'name': 'preset 1'},
            'uuid_2': {'uuid': 'uuid_2', 'name': 'preset 2'},
        },
        constants.CONFIG_MAPPING_RULES: {
            'rules': [
                {'preset_id': 'uuid_1', 'rule_type': 'NoteType', 'model_id': 42}
            ],
            'use_easy_mode': False
        },
        constants.CONFIG_REALTIME_CONFIG: {
            'realtime_0': {}
        },
        constants.CONFIG_CONFIGURATION: {
            'service_enabled': {'ServiceA': True, 'ServiceB': False},
            'service_config': {'ServiceA': {'api_key': 'secret_key'}, 'ServiceB': {}},
            'hypertts_pro_api_key': 'secret_pro_api_key',
            'user_uuid': 'user_uuid_1'
        }
    }


def get_pro_only_config():
    """a HyperTTS Pro user who has no presets yet: the API key is the only thing they would be
    upset to lose"""
    return {
        constants.CONFIG_SCHEMA: constants.CONFIG_SCHEMA_VERSION,
        constants.CONFIG_PRESETS: {},
        constants.CONFIG_CONFIGURATION: {
            'service_enabled': {},
            'service_config': {},
            'hypertts_pro_api_key': 'secret_pro_api_key',
            'use_vocabai_api': True,
            'user_uuid': 'user_uuid_1'
        }
    }


def get_backup_manager():
    anki_utils = testing_utils.MockAnkiUtils({})
    return config_backup.ConfigBackupManager(anki_utils), anki_utils


class ConfigStatsTests(unittest.TestCase):

    def test_analyze_populated_config(self):
        stats = config_backup.analyze_config(get_populated_config())
        self.assertEqual(stats.schema_version, constants.CONFIG_SCHEMA_VERSION)
        self.assertEqual(stats.preset_count, 2)
        self.assertEqual(stats.mapping_rule_count, 1)
        self.assertEqual(stats.realtime_config_count, 1)
        # ServiceB has an empty configuration, it doesn't count
        self.assertEqual(stats.service_config_count, 1)
        self.assertEqual(stats.service_enabled_count, 1)
        self.assertEqual(stats.user_uuid, 'user_uuid_1')
        self.assertEqual(stats.has_user_uuid(), True)
        self.assertEqual(stats.pro_api_key_set, True)
        self.assertEqual(stats.has_user_data(), True)
        self.assertEqual(stats.looks_empty(), False)
        self.assertEqual(stats.looks_wiped(), False)

    def test_analyze_empty_config(self):
        stats = config_backup.analyze_config({})
        self.assertEqual(stats.preset_count, 0)
        self.assertEqual(stats.schema_version, None)
        self.assertEqual(stats.looks_empty(), True)
        self.assertEqual(stats.looks_wiped(), True)

    def test_analyze_default_config_json(self):
        # this is what anki hands us back when meta.json cannot be read: the packaged defaults
        default_config = {
            'configuration': {},
            'preferences': {},
            'presets': {},
            'mapping_rules': {},
            'batch_config': {},
            'realtime_config': {},
            'default_presets': {}
        }
        stats = config_backup.analyze_config(default_config)
        self.assertEqual(stats.looks_wiped(), True)

    def test_analyze_config_installed_but_no_data(self):
        # a fresh install which has been started once: no user data, but the user_uuid is there.
        # this is not a wiped configuration.
        config = {
            constants.CONFIG_SCHEMA: constants.CONFIG_SCHEMA_VERSION,
            constants.CONFIG_CONFIGURATION: {'user_uuid': 'user_uuid_1'}
        }
        stats = config_backup.analyze_config(config)
        self.assertEqual(stats.looks_empty(), True)
        self.assertEqual(stats.looks_wiped(), False)

    def test_analyze_config_free_services_only(self):
        # a user who only uses free services has no service_config and no API key, but they have
        # enabled services: that is user data, and losing it must not be mistaken for an empty
        # configuration
        config = {
            constants.CONFIG_SCHEMA: constants.CONFIG_SCHEMA_VERSION,
            constants.CONFIG_CONFIGURATION: {
                'user_uuid': 'user_uuid_1',
                'service_enabled': {'GoogleTranslate': True},
                'service_config': {'GoogleTranslate': {}}
            }
        }
        stats = config_backup.analyze_config(config)
        self.assertEqual(stats.service_enabled_count, 1)
        self.assertEqual(stats.has_user_data(), True)

    def test_analyze_config_preferences_only(self):
        config = {
            constants.CONFIG_PREFERENCES: {'keyboard_shortcuts': {'shortcut_editor_add_audio': 'A'}}
        }
        stats = config_backup.analyze_config(config)
        self.assertEqual(stats.preferences_count, 1)
        self.assertEqual(stats.has_user_data(), True)

    def test_analyze_config_default_presets(self):
        config = {constants.CONFIG_DEFAULT_PRESETS: {'42': 'uuid_1'}}
        self.assertEqual(config_backup.analyze_config(config).has_user_data(), True)

    def test_analyze_garbage_config(self):
        # never raise, whatever we are handed
        for garbage in [None, [], 'string', 42, {'presets': 'not a dict'},
                {'mapping_rules': {'rules': 'not a list'}}, {'configuration': []}]:
            stats = config_backup.analyze_config(garbage)
            self.assertEqual(stats.preset_count, 0)

    def test_analyze_legacy_config(self):
        # a schema 0 configuration, presets live in batch_config
        config = {
            constants.CONFIG_BATCH_CONFIG: {'preset 1': {}},
        }
        stats = config_backup.analyze_config(config)
        self.assertEqual(stats.legacy_batch_config_count, 1)
        self.assertEqual(stats.has_user_data(), True)
        self.assertEqual(stats.looks_wiped(), False)


class AnomalyDetectionTests(unittest.TestCase):

    def test_no_previous_config(self):
        current = config_backup.analyze_config({})
        self.assertEqual(config_backup.detect_anomalies(None, current), [])

    def test_no_change(self):
        stats = config_backup.analyze_config(get_populated_config())
        self.assertEqual(config_backup.detect_anomalies(stats, stats), [])

    def test_previous_config_empty(self):
        # there was nothing to lose
        previous = config_backup.analyze_config({})
        current = config_backup.analyze_config({})
        self.assertEqual(config_backup.detect_anomalies(previous, current), [])

    def test_config_wiped(self):
        previous = config_backup.analyze_config(get_populated_config())
        current = config_backup.analyze_config({})
        anomalies = config_backup.detect_anomalies(previous, current)
        messages = [anomaly.message for anomaly in anomalies]
        self.assertEqual(len(anomalies), 2)
        self.assertEqual(set([anomaly.severity for anomaly in anomalies]),
            {config_backup.ANOMALY_SEVERITY_ERROR})
        self.assertIn('user_uuid disappeared', messages[0])
        self.assertIn('configuration is empty', messages[1])

    def test_user_uuid_disappeared_from_empty_config(self):
        # the previous configuration had nothing in it but the user_uuid: losing that is still worth
        # reporting, it means the configuration was replaced rather than edited
        previous = config_backup.analyze_config({
            constants.CONFIG_CONFIGURATION: {'user_uuid': 'user_uuid_1'}})
        anomalies = config_backup.detect_anomalies(previous, config_backup.analyze_config({}))
        self.assertEqual(len(anomalies), 1)
        self.assertIn('user_uuid disappeared', anomalies[0].message)

    def test_user_uuid_disappeared(self):
        previous = config_backup.analyze_config(get_populated_config())
        current_config = get_populated_config()
        del current_config[constants.CONFIG_CONFIGURATION]['user_uuid']
        anomalies = config_backup.detect_anomalies(previous, config_backup.analyze_config(current_config))
        messages = [anomaly.message for anomaly in anomalies]
        self.assertEqual(len(anomalies), 1)
        self.assertIn('user_uuid disappeared', messages[0])
        self.assertEqual(anomalies[0].severity, config_backup.ANOMALY_SEVERITY_ERROR)

    def test_schema_disappeared(self):
        previous = config_backup.analyze_config(get_populated_config())
        current_config = get_populated_config()
        del current_config[constants.CONFIG_SCHEMA]
        anomalies = config_backup.detect_anomalies(previous, config_backup.analyze_config(current_config))
        self.assertEqual(len(anomalies), 1)
        self.assertIn('config_schema disappeared', anomalies[0].message)
        self.assertEqual(anomalies[0].severity, config_backup.ANOMALY_SEVERITY_ERROR)

    def test_schema_went_backwards(self):
        previous = config_backup.analyze_config(get_populated_config())
        current_config = get_populated_config()
        current_config[constants.CONFIG_SCHEMA] = 2
        anomalies = config_backup.detect_anomalies(previous, config_backup.analyze_config(current_config))
        self.assertEqual(len(anomalies), 1)
        self.assertIn('config_schema went backwards', anomalies[0].message)

    def test_presets_disappeared(self):
        # could be a legitimate user action (deleting all presets), reported as a warning
        previous = config_backup.analyze_config(get_populated_config())
        current_config = get_populated_config()
        current_config[constants.CONFIG_PRESETS] = {}
        anomalies = config_backup.detect_anomalies(previous, config_backup.analyze_config(current_config))
        self.assertEqual(len(anomalies), 1)
        self.assertIn('all presets disappeared', anomalies[0].message)
        self.assertEqual(anomalies[0].severity, config_backup.ANOMALY_SEVERITY_WARNING)

    def test_api_key_disappeared(self):
        previous = config_backup.analyze_config(get_populated_config())
        current_config = get_populated_config()
        current_config[constants.CONFIG_CONFIGURATION]['hypertts_pro_api_key'] = None
        anomalies = config_backup.detect_anomalies(previous, config_backup.analyze_config(current_config))
        self.assertEqual(len(anomalies), 1)
        self.assertIn('API key disappeared', anomalies[0].message)
        self.assertEqual(anomalies[0].severity, config_backup.ANOMALY_SEVERITY_WARNING)

    def test_user_emptied_their_own_configuration(self):
        # the user deleted their last preset and removed their API key. the configuration is empty,
        # but it is still their configuration: report what disappeared, don't claim it was lost
        previous = config_backup.analyze_config(get_pro_only_config())
        emptied_config = get_pro_only_config()
        emptied_config[constants.CONFIG_CONFIGURATION]['hypertts_pro_api_key'] = None
        anomalies = config_backup.detect_anomalies(previous,
            config_backup.analyze_config(emptied_config))
        self.assertEqual([anomaly.severity for anomaly in anomalies],
            [config_backup.ANOMALY_SEVERITY_WARNING])
        self.assertIn('API key disappeared', anomalies[0].message)

    def test_user_uuid_changed(self):
        # a freshly generated user_uuid means the configuration was regenerated from defaults
        previous = config_backup.analyze_config(get_populated_config())
        current_config = get_populated_config()
        current_config[constants.CONFIG_CONFIGURATION]['user_uuid'] = 'brand_new_uuid'
        anomalies = config_backup.detect_anomalies(previous,
            config_backup.analyze_config(current_config))
        self.assertEqual(len(anomalies), 1)
        self.assertIn('user_uuid changed', anomalies[0].message)
        self.assertEqual(anomalies[0].severity, config_backup.ANOMALY_SEVERITY_ERROR)

    def test_config_wiped_keeps_user_uuid(self):
        # an empty configuration which kept the user_uuid of the configuration we last saw is the
        # user emptying their own configuration, not data loss
        previous = config_backup.analyze_config(get_populated_config())
        emptied_config = {
            constants.CONFIG_SCHEMA: constants.CONFIG_SCHEMA_VERSION,
            constants.CONFIG_CONFIGURATION: {'user_uuid': 'user_uuid_1'}
        }
        anomalies = config_backup.detect_anomalies(previous,
            config_backup.analyze_config(emptied_config))
        severities = set([anomaly.severity for anomaly in anomalies])
        self.assertEqual(severities, {config_backup.ANOMALY_SEVERITY_WARNING})

    def test_preset_added(self):
        # normal operation, no anomaly
        previous = config_backup.analyze_config(get_populated_config())
        current_config = get_populated_config()
        current_config[constants.CONFIG_PRESETS]['uuid_3'] = {'uuid': 'uuid_3', 'name': 'preset 3'}
        self.assertEqual(config_backup.detect_anomalies(previous,
            config_backup.analyze_config(current_config)), [])


class ConfigBackupManagerTests(unittest.TestCase):

    def test_save_backup(self):
        backup_manager, anki_utils = get_backup_manager()
        config = get_populated_config()

        filename = backup_manager.save_backup(config)
        self.assertNotEqual(filename, None)
        self.assertTrue(filename.startswith(constants.CONFIG_BACKUP_FILE_PREFIX))
        self.assertTrue(filename.endswith(constants.CONFIG_BACKUP_FILE_EXTENSION))

        # the file is inside user_files/config_backup
        expected_dir = os.path.join(anki_utils.get_user_files_dir(), constants.CONFIG_BACKUP_DIR_NAME)
        self.assertEqual(backup_manager.get_backup_dir(), expected_dir)
        filepath = os.path.join(expected_dir, filename)
        self.assertTrue(os.path.isfile(filepath))

        # the file contains the full configuration plus metadata
        with open(filepath, 'r', encoding='utf-8') as file_handle:
            backup_data = json.load(file_handle)
        self.assertEqual(backup_data[constants.CONFIG_BACKUP_KEY_CONFIG], config)
        metadata = backup_data[constants.CONFIG_BACKUP_KEY_METADATA]
        self.assertEqual(metadata['stats']['preset_count'], 2)
        self.assertEqual(metadata['config_hash'], config_backup.config_hash(config))
        self.assertNotEqual(metadata['timestamp'], None)

        # no temporary files left behind
        self.assertEqual(os.listdir(expected_dir), [filename])

    def test_save_backup_identical_config(self):
        # saving the same configuration twice should only produce a single backup
        backup_manager, anki_utils = get_backup_manager()
        config = get_populated_config()

        self.assertNotEqual(backup_manager.save_backup(config), None)
        anki_utils.tick_time()
        self.assertEqual(backup_manager.save_backup(config), None)
        self.assertEqual(len(backup_manager.list_backups()), 1)

        # but a modified configuration does get backed up
        config[constants.CONFIG_PRESETS]['uuid_3'] = {'uuid': 'uuid_3', 'name': 'preset 3'}
        anki_utils.tick_time()
        self.assertNotEqual(backup_manager.save_backup(config), None)
        self.assertEqual(len(backup_manager.list_backups()), 2)

    def test_save_backup_empty_config(self):
        # an empty configuration is not worth backing up, and would push out good backups
        backup_manager, anki_utils = get_backup_manager()
        self.assertEqual(backup_manager.save_backup({}), None)
        self.assertEqual(backup_manager.list_backups(), [])

    def test_save_backup_same_timestamp(self):
        # several backups within the same second: filenames must not collide, and must still sort
        # from oldest to newest
        backup_manager, anki_utils = get_backup_manager()
        config = get_populated_config()
        filenames = []
        for i in range(12):
            config[constants.CONFIG_PRESETS][f'uuid_new_{i}'] = {'uuid': f'uuid_new_{i}', 'name': f'p{i}'}
            filenames.append(backup_manager.save_backup(config))
        self.assertEqual(len(set(filenames)), 12)
        self.assertEqual(len(backup_manager.list_backups()), 12)
        # the most recent backup (the one with the most presets) comes first
        self.assertEqual(backup_manager.list_backups()[0].filename, filenames[-1])
        self.assertEqual(backup_manager.get_latest_backup().stats.preset_count, 2 + 12)

    def test_backups_sorted_most_recent_first(self):
        backup_manager, anki_utils = get_backup_manager()
        config = get_populated_config()
        for i in range(3):
            config[constants.CONFIG_PRESETS][f'uuid_new_{i}'] = {'uuid': f'uuid_new_{i}', 'name': f'p{i}'}
            backup_manager.save_backup(config)
            anki_utils.tick_time()

        backup_list = backup_manager.list_backups()
        self.assertEqual(len(backup_list), 3)
        timestamps = [backup_info.timestamp for backup_info in backup_list]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
        # the most recent backup has all 3 new presets
        self.assertEqual(backup_list[0].stats.preset_count, 5)
        latest = backup_manager.get_latest_backup()
        self.assertEqual(latest.filename, backup_list[0].filename)

    def test_prune_backups(self):
        backup_manager, anki_utils = get_backup_manager()
        config = get_populated_config()
        for i in range(constants.CONFIG_BACKUP_MAX_COUNT + 5):
            config[constants.CONFIG_PRESETS][f'uuid_new_{i}'] = {'uuid': f'uuid_new_{i}', 'name': f'p{i}'}
            backup_manager.save_backup(config)
            anki_utils.tick_time()

        backup_list = backup_manager.list_backups()
        self.assertEqual(len(backup_list), constants.CONFIG_BACKUP_MAX_COUNT)
        # the most recent ones were kept
        self.assertEqual(backup_list[0].stats.preset_count,
            2 + constants.CONFIG_BACKUP_MAX_COUNT + 5)

    def test_backup_info_valid(self):
        backup_manager, anki_utils = get_backup_manager()
        filename = backup_manager.save_backup(get_populated_config())
        backup_info = backup_manager.get_backup_info(filename)
        self.assertEqual(backup_info.looks_valid(), True)
        self.assertEqual(backup_info.status_str(), 'OK')
        self.assertEqual(backup_info.parse_error, None)
        self.assertEqual(backup_info.stats.preset_count, 2)
        self.assertNotEqual(backup_info.size_bytes, 0)
        self.assertEqual(backup_info.timestamp_str(), anki_utils.get_current_time().strftime('%Y-%m-%d %H:%M:%S'))

    def test_backup_info_corrupted(self):
        backup_manager, anki_utils = get_backup_manager()
        backup_manager.save_backup(get_populated_config())
        os.makedirs(backup_manager.get_backup_dir(), exist_ok=True)

        # a truncated backup file
        truncated_filename = f'{constants.CONFIG_BACKUP_FILE_PREFIX}20200101_010101.json'
        with open(os.path.join(backup_manager.get_backup_dir(), truncated_filename), 'w') as f:
            f.write('{"config": {"presets": ')
        # an empty backup file
        empty_filename = f'{constants.CONFIG_BACKUP_FILE_PREFIX}20200101_010102.json'
        with open(os.path.join(backup_manager.get_backup_dir(), empty_filename), 'w') as f:
            f.write('')

        truncated_info = backup_manager.get_backup_info(truncated_filename)
        self.assertEqual(truncated_info.looks_valid(), False)
        self.assertIn('invalid JSON', truncated_info.parse_error)
        self.assertIn('Corrupted', truncated_info.status_str())
        # a corrupted file still shows a timestamp, taken from the file itself
        self.assertNotEqual(truncated_info.timestamp, None)

        empty_info = backup_manager.get_backup_info(empty_filename)
        self.assertEqual(empty_info.looks_valid(), False)
        self.assertEqual(empty_info.parse_error, 'file is empty')

        # get_latest_valid_backup skips the corrupted files
        self.assertEqual(backup_manager.get_latest_valid_backup().stats.preset_count, 2)

        # restoring a corrupted backup is refused
        self.assertRaises(errors.ConfigBackupError, backup_manager.load_backup_config, truncated_filename)
        self.assertRaises(errors.ConfigBackupError, backup_manager.load_backup_config, empty_filename)

    def test_backup_info_empty_config(self):
        backup_manager, anki_utils = get_backup_manager()
        os.makedirs(backup_manager.get_backup_dir(), exist_ok=True)
        filename = f'{constants.CONFIG_BACKUP_FILE_PREFIX}20200101_010101.json'
        config_backup.atomic_write_json(os.path.join(backup_manager.get_backup_dir(), filename),
            {constants.CONFIG_BACKUP_KEY_CONFIG: {}})
        backup_info = backup_manager.get_backup_info(filename)
        self.assertEqual(backup_info.looks_valid(), False)
        self.assertIn('Empty', backup_info.status_str())
        self.assertRaises(errors.ConfigBackupError, backup_manager.load_backup_config, filename)

    def test_load_backup_bare_config(self):
        # a file which contains a bare configuration dict (for example copied by hand from
        # meta.json) can also be restored
        backup_manager, anki_utils = get_backup_manager()
        os.makedirs(backup_manager.get_backup_dir(), exist_ok=True)
        filename = f'{constants.CONFIG_BACKUP_FILE_PREFIX}20200101_010101.json'
        config_backup.atomic_write_json(os.path.join(backup_manager.get_backup_dir(), filename),
            get_populated_config())
        backup_info = backup_manager.get_backup_info(filename)
        self.assertEqual(backup_info.looks_valid(), True)
        self.assertEqual(backup_manager.load_backup_config(filename), get_populated_config())

    def test_load_backup_missing_file(self):
        backup_manager, anki_utils = get_backup_manager()
        self.assertRaises(errors.ConfigBackupError, backup_manager.load_backup_config, 'does_not_exist.json')

    def test_list_backups_no_directory(self):
        backup_manager, anki_utils = get_backup_manager()
        self.assertEqual(backup_manager.list_backups(), [])
        self.assertEqual(backup_manager.get_latest_backup(), None)
        self.assertEqual(backup_manager.get_latest_valid_backup(), None)

    def test_list_backups_ignores_unrelated_files(self):
        backup_manager, anki_utils = get_backup_manager()
        backup_manager.save_backup(get_populated_config())
        with open(os.path.join(backup_manager.get_backup_dir(), 'notes.txt'), 'w') as f:
            f.write('hello')
        self.assertEqual(len(backup_manager.list_backups()), 1)

    def test_atomic_write_json_keeps_previous_file(self):
        backup_manager, anki_utils = get_backup_manager()
        filepath = os.path.join(backup_manager.get_backup_dir(), 'test.json')
        config_backup.atomic_write_json(filepath, {'a': 1})

        # a serialization failure must not destroy the existing file
        class NotSerializable():
            pass
        config_backup.atomic_write_json(filepath, {'b': NotSerializable()})
        with open(filepath, 'r', encoding='utf-8') as file_handle:
            # default=str means anything can be serialized, but the file must still be valid json
            self.assertIn('b', json.load(file_handle))

        # and no temporary files are left over
        leftover = [f for f in os.listdir(backup_manager.get_backup_dir()) if f.endswith('.tmp')]
        self.assertEqual(leftover, [])

    def test_check_config_before_write(self):
        backup_manager, anki_utils = get_backup_manager()
        config = get_populated_config()

        # nothing on disk yet, no anomaly
        self.assertEqual(backup_manager.check_config_before_write(config), True)
        self.assertEqual(anki_utils.config_anomalies, [])

        backup_manager.save_backup(config)

        # writing the same config again: fine
        self.assertEqual(backup_manager.check_config_before_write(config), True)
        self.assertEqual(anki_utils.config_anomalies, [])

        # writing an empty config over it: refused and reported
        self.assertEqual(backup_manager.check_config_before_write({}), False)
        self.assertEqual(len(anki_utils.config_anomalies), 2)
        anomaly = anki_utils.config_anomalies[1]
        self.assertEqual(anomaly['severity'], config_backup.ANOMALY_SEVERITY_ERROR)
        self.assertIn('user_uuid disappeared', anki_utils.config_anomalies[0]['message'])
        self.assertIn('configuration is empty', anomaly['message'])
        # the report contains diagnostics, but no secret values
        self.assertEqual(anomaly['extra']['previous']['preset_count'], 2)
        self.assertEqual(anomaly['extra']['current']['preset_count'], 0)
        self.assertNotIn('secret_key', json.dumps(anomaly['extra']))
        self.assertNotIn('secret_pro_api_key', json.dumps(anomaly['extra']))

    def test_check_config_before_write_deleting_presets(self):
        # deleting all presets is a legitimate user action: reported as a warning, but allowed
        backup_manager, anki_utils = get_backup_manager()
        config = get_populated_config()
        backup_manager.save_backup(config)

        config_without_presets = get_populated_config()
        config_without_presets[constants.CONFIG_PRESETS] = {}
        self.assertEqual(backup_manager.check_config_before_write(config_without_presets), True)
        self.assertEqual(len(anki_utils.config_anomalies), 1)
        self.assertEqual(anki_utils.config_anomalies[0]['severity'],
            config_backup.ANOMALY_SEVERITY_WARNING)

    def test_check_config_before_write_removing_last_api_key(self):
        # removing the HyperTTS Pro API key when it is the only thing configured empties the
        # configuration, but it is a deliberate user action and must go through
        backup_manager, anki_utils = get_backup_manager()
        backup_manager.save_backup(get_pro_only_config())

        config_without_api_key = get_pro_only_config()
        config_without_api_key[constants.CONFIG_CONFIGURATION]['hypertts_pro_api_key'] = None
        self.assertEqual(config_backup.analyze_config(config_without_api_key).looks_empty(), True)
        self.assertEqual(backup_manager.check_config_before_write(config_without_api_key), True)
        self.assertEqual([anomaly['severity'] for anomaly in anki_utils.config_anomalies],
            [config_backup.ANOMALY_SEVERITY_WARNING])

        # and the empty configuration is backed up, so it becomes the baseline: saving it again
        # reports nothing at all
        anki_utils.tick_time()
        backup_manager.save_backup(config_without_api_key)
        anki_utils.config_anomalies = []
        self.assertEqual(backup_manager.check_config_before_write(config_without_api_key), True)
        self.assertEqual(anki_utils.config_anomalies, [])

    def test_check_config_before_write_removing_last_preset(self):
        backup_manager, anki_utils = get_backup_manager()
        config = {
            constants.CONFIG_SCHEMA: constants.CONFIG_SCHEMA_VERSION,
            constants.CONFIG_PRESETS: {'uuid_1': {'uuid': 'uuid_1', 'name': 'preset 1'}},
            constants.CONFIG_CONFIGURATION: {'user_uuid': 'user_uuid_1'}
        }
        backup_manager.save_backup(config)

        config_without_presets = copy.deepcopy(config)
        config_without_presets[constants.CONFIG_PRESETS] = {}
        self.assertEqual(backup_manager.check_config_before_write(config_without_presets), True)
        self.assertEqual([anomaly['severity'] for anomaly in anki_utils.config_anomalies],
            [config_backup.ANOMALY_SEVERITY_WARNING])

    def test_check_config_before_write_wiped_config_with_different_uuid(self):
        # a configuration which is empty and carries a freshly generated user_uuid is the issue #360
        # scenario, it must still be refused
        backup_manager, anki_utils = get_backup_manager()
        backup_manager.save_backup(get_populated_config())
        regenerated_config = {
            constants.CONFIG_SCHEMA: constants.CONFIG_SCHEMA_VERSION,
            constants.CONFIG_CONFIGURATION: {'user_uuid': 'brand_new_uuid'}
        }
        self.assertEqual(backup_manager.check_config_before_write(regenerated_config), False)
        self.assertEqual(anki_utils.config_anomalies[0]['severity'],
            config_backup.ANOMALY_SEVERITY_ERROR)

    def test_meta_json_status_missing(self):
        backup_manager, anki_utils = get_backup_manager()
        status = backup_manager.get_meta_json_status()
        self.assertEqual(status['exists'], False)
        self.assertEqual(status['parse_error'], None)

    def test_meta_json_status_valid(self):
        backup_manager, anki_utils = get_backup_manager()
        with open(backup_manager.get_meta_json_path(), 'w', encoding='utf-8') as file_handle:
            json.dump({'config': get_populated_config(), 'disabled': False}, file_handle)
        status = backup_manager.get_meta_json_status()
        self.assertEqual(status['exists'], True)
        self.assertEqual(status['parse_error'], None)
        self.assertEqual(status['has_config_key'], True)
        self.assertEqual(status['config_key_count'], len(get_populated_config()))
        self.assertGreater(status['size'], 0)

    def test_meta_json_status_truncated(self):
        backup_manager, anki_utils = get_backup_manager()
        # this is the failure mode described in issue #360: anki truncates meta.json before writing
        # it, so an interrupted write leaves invalid json behind, and anki then silently returns the
        # packaged default configuration
        with open(backup_manager.get_meta_json_path(), 'w', encoding='utf-8') as file_handle:
            file_handle.write('{"config": {"presets": {"uuid_1": ')
        status = backup_manager.get_meta_json_status()
        self.assertEqual(status['exists'], True)
        self.assertIn('invalid JSON', status['parse_error'])

    def test_check_startup_config_state(self):
        backup_manager, anki_utils = get_backup_manager()
        config = get_populated_config()
        # normal startup
        self.assertEqual(backup_manager.check_startup_config_state(config), True)
        self.assertEqual(anki_utils.config_anomalies, [])

    def test_check_startup_config_state_config_lost(self):
        backup_manager, anki_utils = get_backup_manager()
        backup_manager.save_backup(get_populated_config())

        # we start up with an empty configuration while a backup shows we had data: don't trust it
        self.assertEqual(backup_manager.check_startup_config_state({}), False)
        self.assertEqual(len(anki_utils.config_anomalies), 1)
        self.assertIn('configuration is empty at startup', anki_utils.config_anomalies[0]['message'])
        self.assertEqual(anki_utils.config_anomalies[0]['severity'],
            config_backup.ANOMALY_SEVERITY_ERROR)

    def test_check_startup_config_state_meta_json_corrupted(self):
        backup_manager, anki_utils = get_backup_manager()
        with open(backup_manager.get_meta_json_path(), 'w', encoding='utf-8') as file_handle:
            file_handle.write('{"config": ')

        # even without any backup, a meta.json which doesn't parse means the configuration anki
        # gave us is not the user's configuration
        self.assertEqual(backup_manager.check_startup_config_state({}), False)
        self.assertEqual(len(anki_utils.config_anomalies), 1)
        self.assertIn("meta.json could not be parsed", anki_utils.config_anomalies[0]['message'])

    def test_check_startup_config_state_looks_like_first_install(self):
        # the exact issue #360 sequence: anki cannot read meta.json, hands us the packaged defaults,
        # and something (previously HyperTTS itself) has already stamped a fresh user_uuid in. this
        # must still be recognized as a lost configuration, not as a new install.
        backup_manager, anki_utils = get_backup_manager()
        backup_manager.save_backup(get_populated_config())

        fresh_install_looking_config = {
            constants.CONFIG_SCHEMA: constants.CONFIG_SCHEMA_VERSION,
            constants.CONFIG_PRESETS: {},
            constants.CONFIG_PREFERENCES: {},
            constants.CONFIG_CONFIGURATION: {
                'user_uuid': 'brand_new_uuid',
                'service_enabled': {},
                'service_config': {},
                'hypertts_pro_api_key': None,
                'trial_registration_step': 'new_install'
            }
        }
        self.assertEqual(config_backup.analyze_config(fresh_install_looking_config).looks_wiped(), False)
        self.assertEqual(backup_manager.check_startup_config_state(fresh_install_looking_config), False)
        self.assertEqual(len(anki_utils.config_anomalies), 1)
        self.assertIn('configuration is empty at startup', anki_utils.config_anomalies[0]['message'])

    def test_check_startup_config_state_user_emptied_configuration(self):
        # a user who emptied their configuration on purpose: the most recent backup is empty too, so
        # there is nothing to report and writes stay allowed
        backup_manager, anki_utils = get_backup_manager()
        backup_manager.save_backup(get_populated_config())
        anki_utils.tick_time()
        emptied_config = {
            constants.CONFIG_SCHEMA: constants.CONFIG_SCHEMA_VERSION,
            constants.CONFIG_CONFIGURATION: {'user_uuid': 'user_uuid_1'}
        }
        backup_manager.save_backup(emptied_config)
        anki_utils.config_anomalies = []

        self.assertEqual(backup_manager.check_startup_config_state(emptied_config), True)
        self.assertEqual(anki_utils.config_anomalies, [])
        self.assertEqual(backup_manager.check_config_before_write(emptied_config), True)
        self.assertEqual(anki_utils.config_anomalies, [])

    def test_check_startup_config_state_emptied_by_user(self):
        # the user removed their API key in the previous session: at startup their configuration is
        # empty but it is still theirs, nothing to report and writes stay allowed
        backup_manager, anki_utils = get_backup_manager()
        backup_manager.save_backup(get_pro_only_config())
        config_without_api_key = get_pro_only_config()
        config_without_api_key[constants.CONFIG_CONFIGURATION]['hypertts_pro_api_key'] = None

        self.assertEqual(backup_manager.check_startup_config_state(config_without_api_key), True)
        self.assertEqual(anki_utils.config_anomalies, [])

    def test_check_startup_config_state_first_install(self):
        # empty configuration, no backups: this is a new install, nothing to report
        backup_manager, anki_utils = get_backup_manager()
        self.assertEqual(backup_manager.check_startup_config_state({}), True)
        self.assertEqual(anki_utils.config_anomalies, [])


class HyperTTSConfigBackupTests(unittest.TestCase):
    """the configuration backup / restore behavior of the HyperTTS object itself"""

    def build_hypertts_instance(self, config, previous_instance=None):
        """build a hypertts instance. pass previous_instance to simulate anki restarting with the
        configuration backups (and meta.json) of a previous session in place."""
        config_gen = testing_utils.TestConfigGenerator()
        user_files_dir = None
        addon_dir = None
        if previous_instance != None:
            user_files_dir = previous_instance.anki_utils.user_files_dir
            addon_dir = previous_instance.anki_utils.addon_dir
        return config_gen.build_hypertts_instance_test_servicemanager_config(config,
            user_files_dir=user_files_dir, addon_dir=addon_dir)

    def test_startup_takes_backup(self):
        hypertts_instance = self.build_hypertts_instance(get_populated_config())
        backup_list = hypertts_instance.config_backup_manager.list_backups()
        self.assertEqual(len(backup_list), 1)
        self.assertEqual(backup_list[0].stats.preset_count, 2)
        self.assertEqual(hypertts_instance.config_writes_blocked, False)

    def test_startup_no_write_when_no_migration_needed(self):
        # the configuration is already at the current schema, HyperTTS must not write anything on
        # startup (github issue #360)
        hypertts_instance = self.build_hypertts_instance(get_populated_config())
        self.assertEqual(hypertts_instance.anki_utils.written_config, None)

    def test_startup_writes_after_migration(self):
        config = get_populated_config()
        del config[constants.CONFIG_SCHEMA]
        del config[constants.CONFIG_PRESETS]
        del config[constants.CONFIG_MAPPING_RULES]
        config[constants.CONFIG_BATCH_CONFIG] = {'preset 1': {'source': {}}}
        hypertts_instance = self.build_hypertts_instance(config)
        # the migration converted the legacy preset, so the configuration was written
        self.assertNotEqual(hypertts_instance.anki_utils.written_config, None)
        self.assertEqual(hypertts_instance.anki_utils.written_config[constants.CONFIG_SCHEMA],
            constants.CONFIG_SCHEMA_VERSION)
        self.assertEqual(len(hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS]), 1)

    def test_save_preset_takes_backup(self):
        hypertts_instance = self.build_hypertts_instance(get_populated_config())
        backup_count = len(hypertts_instance.config_backup_manager.list_backups())

        hypertts_instance.anki_utils.tick_time()
        preset = config_models.BatchConfig(hypertts_instance.anki_utils)
        preset.name = 'new preset'
        preset.uuid = 'uuid_new'
        hypertts_instance.config[constants.CONFIG_PRESETS][preset.uuid] = {
            'uuid': preset.uuid, 'name': preset.name}
        self.assertEqual(hypertts_instance.persist_config(), True)

        backup_list = hypertts_instance.config_backup_manager.list_backups()
        self.assertEqual(len(backup_list), backup_count + 1)
        self.assertEqual(backup_list[0].stats.preset_count, 3)

    def test_startup_config_lost_blocks_writes(self):
        # first, a normal session which leaves a backup behind
        hypertts_instance = self.build_hypertts_instance(get_populated_config())

        # then a session where anki hands us the packaged defaults instead of the user's config
        broken_hypertts = self.build_hypertts_instance({}, previous_instance=hypertts_instance)
        self.assertEqual(broken_hypertts.config_writes_blocked, True)

        # the user was told about it, and it was reported
        self.assertEqual(len(broken_hypertts.anki_utils.config_anomalies), 1)
        self.assertEqual(broken_hypertts.anki_utils.critical_message_received,
            constants.GUI_TEXT_CONFIG_LOSS_DETECTED)

        # any attempt to save the configuration is refused, the good configuration on disk survives
        broken_hypertts.anki_utils.written_config = None
        self.assertEqual(broken_hypertts.persist_config(), False)
        self.assertEqual(broken_hypertts.anki_utils.written_config, None)
        self.assertEqual(broken_hypertts.anki_utils.critical_message_received,
            constants.GUI_TEXT_CONFIG_LOSS_DETECTED)

        # and the backups are still intact
        self.assertEqual(len(broken_hypertts.config_backup_manager.list_backups()), 1)

    def test_remove_last_api_key(self):
        # a HyperTTS Pro user with no presets removes their API key: their configuration becomes
        # empty, but this is a deliberate action and must be saved (issue #360 follow up)
        hypertts_instance = self.build_hypertts_instance(get_pro_only_config())
        hypertts_instance.anki_utils.written_config = None
        hypertts_instance.anki_utils.tick_time()

        configuration = hypertts_instance.get_configuration()
        configuration.set_hypertts_pro_api_key(None)
        hypertts_instance.save_configuration(configuration)

        written_config = hypertts_instance.anki_utils.written_config
        self.assertNotEqual(written_config, None)
        self.assertEqual(written_config[constants.CONFIG_CONFIGURATION]['hypertts_pro_api_key'], None)
        self.assertEqual(hypertts_instance.get_configuration().hypertts_pro_api_key_set(), False)
        # writes keep working afterwards
        self.assertEqual(hypertts_instance.config_writes_blocked, False)
        self.assertEqual(hypertts_instance.persist_config(), True)
        # the API key can still be recovered from the backup taken at startup
        latest_valid_backup = hypertts_instance.config_backup_manager.get_latest_valid_backup()
        self.assertEqual(latest_valid_backup.stats.pro_api_key_set, True)

    def test_remove_last_preset(self):
        # deleting the last preset of a user who has nothing else configured must also go through
        config = {
            constants.CONFIG_SCHEMA: constants.CONFIG_SCHEMA_VERSION,
            constants.CONFIG_PRESETS: {'uuid_1': {'uuid': 'uuid_1', 'name': 'preset 1'}},
            constants.CONFIG_CONFIGURATION: {'user_uuid': 'user_uuid_1'}
        }
        hypertts_instance = self.build_hypertts_instance(config)
        hypertts_instance.anki_utils.written_config = None
        hypertts_instance.anki_utils.tick_time()

        hypertts_instance.delete_preset('uuid_1')

        self.assertEqual(hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS], {})
        self.assertEqual(hypertts_instance.get_preset_list(), [])
        self.assertEqual(hypertts_instance.config_writes_blocked, False)

    def test_startup_after_removing_last_api_key(self):
        # and the next time anki starts, that empty configuration is not mistaken for a lost one
        hypertts_instance = self.build_hypertts_instance(get_pro_only_config())
        configuration = hypertts_instance.get_configuration()
        configuration.set_hypertts_pro_api_key(None)
        hypertts_instance.anki_utils.tick_time()
        hypertts_instance.save_configuration(configuration)

        next_session = self.build_hypertts_instance(hypertts_instance.config,
            previous_instance=hypertts_instance)
        self.assertEqual(next_session.config_writes_blocked, False)
        self.assertEqual(next_session.anki_utils.config_anomalies, [])

    def test_startup_config_lost_looks_like_first_install(self):
        # what anki + HyperTTS produced before this was fixed: meta.json couldn't be read, so
        # HyperTTS wrote a brand new user_uuid over the packaged defaults. that configuration is
        # still a lost configuration, and must not be written to again (github issue #360)
        hypertts_instance = self.build_hypertts_instance(get_populated_config())

        fresh_install_looking_config = {
            constants.CONFIG_SCHEMA: constants.CONFIG_SCHEMA_VERSION,
            constants.CONFIG_PRESETS: {},
            constants.CONFIG_PREFERENCES: {},
            constants.CONFIG_CONFIGURATION: {
                'user_uuid': 'brand_new_uuid',
                'service_enabled': {},
                'service_config': {},
                'trial_registration_step': 'new_install'
            }
        }
        broken_hypertts = self.build_hypertts_instance(fresh_install_looking_config,
            previous_instance=hypertts_instance)
        self.assertEqual(broken_hypertts.config_writes_blocked, True)
        self.assertEqual(broken_hypertts.anki_utils.written_config, None)
        self.assertEqual(len(broken_hypertts.anki_utils.config_anomalies), 1)

        # no backup was taken of the lost configuration, so the good backup is still the latest one
        backup_list = broken_hypertts.config_backup_manager.list_backups()
        self.assertEqual(len(backup_list), 1)
        self.assertEqual(backup_list[0].stats.preset_count, 2)

        # and it can be restored
        broken_hypertts.restore_config_backup(backup_list[0].filename)
        self.assertEqual(len(broken_hypertts.config[constants.CONFIG_PRESETS]), 2)

    def test_startup_meta_json_corrupted_blocks_writes(self):
        # a meta.json which doesn't parse means anki gave us the packaged defaults. the damaged file
        # may still be recoverable, so nothing must be written over it, even without any backup
        hypertts_instance = self.build_hypertts_instance(get_populated_config())
        meta_json_path = hypertts_instance.config_backup_manager.get_meta_json_path()
        with open(meta_json_path, 'w', encoding='utf-8') as file_handle:
            file_handle.write('{"config": {"presets": {"uuid_1": ')

        broken_hypertts = self.build_hypertts_instance({}, previous_instance=hypertts_instance)
        self.assertEqual(broken_hypertts.config_writes_blocked, True)
        self.assertEqual(broken_hypertts.anki_utils.written_config, None)
        anomaly_messages = [anomaly['message'] for anomaly in broken_hypertts.anki_utils.config_anomalies]
        self.assertEqual(len(anomaly_messages), 2)
        self.assertIn('meta.json could not be parsed', anomaly_messages[0])

    def test_startup_first_install(self):
        # a genuine first install: no backups, nothing to report, writes allowed
        hypertts_instance = self.build_hypertts_instance({})
        self.assertEqual(hypertts_instance.config_writes_blocked, False)
        self.assertEqual(hypertts_instance.anki_utils.config_anomalies, [])
        # the migration stamped the schema version in, so the configuration was written
        self.assertEqual(hypertts_instance.anki_utils.written_config[constants.CONFIG_SCHEMA],
            constants.CONFIG_SCHEMA_VERSION)

    def test_persist_config_refuses_to_wipe_configuration(self):
        hypertts_instance = self.build_hypertts_instance(get_populated_config())
        hypertts_instance.anki_utils.written_config = None

        # simulate the configuration being replaced by anki's packaged defaults while HyperTTS is
        # running, then something triggering a save
        hypertts_instance.config = {}
        self.assertEqual(hypertts_instance.persist_config(), False)
        self.assertEqual(hypertts_instance.anki_utils.written_config, None)
        self.assertEqual(hypertts_instance.config_writes_blocked, True)
        anomaly_messages = [anomaly['message'] for anomaly in hypertts_instance.anki_utils.config_anomalies]
        self.assertEqual(len(anomaly_messages), 2)
        self.assertIn('user_uuid disappeared', anomaly_messages[0])
        self.assertIn('configuration is empty', anomaly_messages[1])

    def test_restore_config_backup(self):
        hypertts_instance = self.build_hypertts_instance(get_populated_config())
        backup_filename = hypertts_instance.config_backup_manager.list_backups()[0].filename

        # the user loses their configuration
        hypertts_instance.anki_utils.tick_time()
        hypertts_instance.config = {}
        self.assertEqual(hypertts_instance.persist_config(), False)

        # and restores it from the backup
        hypertts_instance.anki_utils.tick_time()
        configuration = hypertts_instance.restore_config_backup(backup_filename)
        self.assertEqual(len(hypertts_instance.config[constants.CONFIG_PRESETS]), 2)
        self.assertEqual(hypertts_instance.get_preset_name('uuid_1'), 'preset 1')
        self.assertEqual(configuration.hypertts_pro_api_key, 'secret_pro_api_key')
        # the restored configuration was written to the addon config
        self.assertEqual(len(hypertts_instance.anki_utils.written_config[constants.CONFIG_PRESETS]), 2)
        # writes are allowed again
        self.assertEqual(hypertts_instance.config_writes_blocked, False)

    def test_restore_config_backup_legacy_schema(self):
        # restoring a backup taken by an older version of HyperTTS runs the migrations
        hypertts_instance = self.build_hypertts_instance(get_populated_config())
        backup_manager = hypertts_instance.config_backup_manager
        os.makedirs(backup_manager.get_backup_dir(), exist_ok=True)
        legacy_filename = f'{constants.CONFIG_BACKUP_FILE_PREFIX}20200101_010101.json'
        config_backup.atomic_write_json(
            os.path.join(backup_manager.get_backup_dir(), legacy_filename),
            {constants.CONFIG_BACKUP_KEY_CONFIG: {
                constants.CONFIG_BATCH_CONFIG: {'legacy preset': {'source': {}}}
            }})

        hypertts_instance.restore_config_backup(legacy_filename)
        self.assertEqual(hypertts_instance.config[constants.CONFIG_SCHEMA],
            constants.CONFIG_SCHEMA_VERSION)
        preset_list = hypertts_instance.get_preset_list()
        self.assertEqual([preset.name for preset in preset_list], ['legacy preset'])

    def test_restore_config_backup_keeps_current_config(self):
        # the configuration being replaced is backed up first, so a restore can be undone
        hypertts_instance = self.build_hypertts_instance(get_populated_config())
        backup_filename = hypertts_instance.config_backup_manager.list_backups()[0].filename

        hypertts_instance.anki_utils.tick_time()
        hypertts_instance.config[constants.CONFIG_PRESETS]['uuid_3'] = {'uuid': 'uuid_3', 'name': 'preset 3'}
        hypertts_instance.persist_config()

        hypertts_instance.anki_utils.tick_time()
        hypertts_instance.restore_config_backup(backup_filename)
        self.assertEqual(len(hypertts_instance.config[constants.CONFIG_PRESETS]), 2)

        # the 3 preset configuration is still available as a backup
        backup_list = hypertts_instance.config_backup_manager.list_backups()
        preset_counts = [backup_info.stats.preset_count for backup_info in backup_list]
        self.assertIn(3, preset_counts)

    def test_restore_config_backup_error(self):
        hypertts_instance = self.build_hypertts_instance(get_populated_config())
        self.assertRaises(errors.ConfigBackupError, hypertts_instance.restore_config_backup,
            'does_not_exist.json')
