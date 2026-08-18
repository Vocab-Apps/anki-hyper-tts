"""configuration backups and configuration health checks.

background: github issue #360, users report that their HyperTTS configuration (presets, API keys)
disappears. HyperTTS stores its configuration through anki's addon config API, which persists
everything into a single meta.json file in the addon directory. anki writes that file
non-atomically (open(path, 'w') followed by json.dump) and silently returns an empty dict when the
file cannot be parsed, which means an interrupted write, a cloud-sync race or an antivirus lock can
turn the user's configuration into anki's packaged defaults. HyperTTS would then happily write those
defaults back, making the loss permanent.

this module provides:
- a rolling set of configuration backups in user_files/config_backup/ (user_files survives addon
  upgrades), written atomically
- statistics about a configuration (preset count, whether an API key is set, ...) so that the
  preferences screen can tell the user whether a backup looks correct
- detection of anomalies (configuration wiped, presets gone, schema going backwards, meta.json
  which doesn't parse), reported to sentry so we can finally diagnose issue #360
"""

import dataclasses
import datetime
import hashlib
import json
import os
import tempfile
from typing import Any, Dict, List, Optional

from . import constants
from . import errors
from . import version

from . import logging_utils
logger = logging_utils.get_child_logger(__name__)


# severity of a configuration anomaly, used to decide how loudly we report it
ANOMALY_SEVERITY_WARNING = 'warning'
ANOMALY_SEVERITY_ERROR = 'error'


@dataclasses.dataclass
class ConfigAnomaly():
    message: str
    severity: str


@dataclasses.dataclass
class ConfigStats():
    """everything we want to know about a configuration without looking at any secret value"""
    schema_version: Optional[int] = None
    preset_count: int = 0
    mapping_rule_count: int = 0
    realtime_config_count: int = 0
    service_config_count: int = 0
    service_enabled_count: int = 0
    legacy_batch_config_count: int = 0
    default_preset_count: int = 0
    preferences_count: int = 0
    user_uuid: Optional[str] = None
    pro_api_key_set: bool = False
    top_level_key_count: int = 0

    def has_user_uuid(self) -> bool:
        return bool(self.user_uuid)

    def has_user_data(self) -> bool:
        """whether this configuration contains anything the user would be upset to lose. kept
        deliberately broad: everything here is empty in anki's packaged defaults, so anything at all
        being set means we are looking at a configuration the user worked on."""
        return (self.preset_count > 0 or
            self.mapping_rule_count > 0 or
            self.realtime_config_count > 0 or
            self.service_config_count > 0 or
            self.service_enabled_count > 0 or
            self.legacy_batch_config_count > 0 or
            self.default_preset_count > 0 or
            self.preferences_count > 0 or
            self.pro_api_key_set)

    def looks_empty(self) -> bool:
        return not self.has_user_data()

    def looks_wiped(self) -> bool:
        """no user data at all, not even the anonymous user_uuid which every installation gets on
        its first startup. a configuration in that state was never produced by the user going
        through the HyperTTS screens, it means we failed to read the real configuration."""
        return self.looks_empty() and not self.has_user_uuid()

    def same_installation_as(self, other: 'ConfigStats') -> bool:
        """whether both configurations belong to the same HyperTTS installation. the anonymous
        user_uuid is generated once, when HyperTTS is first installed, and no screen ever changes
        it: a configuration carrying the same user_uuid as our last backup is the user's own
        configuration, no matter how much of it they emptied. a configuration with no user_uuid, or
        with a freshly generated one, is a configuration we failed to read (github issue #360)."""
        return self.has_user_uuid() and self.user_uuid == other.user_uuid

    def describe(self) -> str:
        api_key_str = 'API key set' if self.pro_api_key_set else 'no API key'
        return (f'{self.preset_count} presets, {self.mapping_rule_count} preset rules, '
            f'{self.service_config_count} configured services, {api_key_str}, '
            f'schema {self.schema_version}')

    def as_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class ConfigBackupInfo():
    """a configuration backup file on disk, as displayed on the preferences screen"""
    filename: str
    filepath: str
    size_bytes: int = 0
    timestamp: Optional[datetime.datetime] = None
    stats: Optional[ConfigStats] = None
    config_hash: Optional[str] = None
    hypertts_version: Optional[str] = None
    parse_error: Optional[str] = None

    def looks_valid(self) -> bool:
        """whether this backup is worth restoring"""
        if self.parse_error != None:
            return False
        if self.stats == None:
            return False
        return self.stats.has_user_data()

    def timestamp_str(self) -> str:
        if self.timestamp == None:
            return 'unknown'
        return self.timestamp.strftime('%Y-%m-%d %H:%M:%S')

    def status_str(self) -> str:
        if self.parse_error != None:
            return f'Corrupted: {self.parse_error}'
        if self.stats == None:
            return 'Corrupted: no configuration found'
        if self.stats.looks_empty():
            return 'Empty (nothing to restore)'
        return 'OK'


def analyze_config(config) -> ConfigStats:
    """compute statistics on a raw configuration dict. never raises, never looks at secret values,
    tolerates any kind of corrupted content."""
    stats = ConfigStats()
    if not isinstance(config, dict):
        return stats

    stats.top_level_key_count = len(config)

    schema_version = config.get(constants.CONFIG_SCHEMA, None)
    if isinstance(schema_version, int):
        stats.schema_version = schema_version

    def dict_len(key) -> int:
        value = config.get(key, None)
        if isinstance(value, dict):
            return len(value)
        return 0

    stats.preset_count = dict_len(constants.CONFIG_PRESETS)
    stats.realtime_config_count = dict_len(constants.CONFIG_REALTIME_CONFIG)
    stats.legacy_batch_config_count = dict_len(constants.CONFIG_BATCH_CONFIG)
    stats.default_preset_count = dict_len(constants.CONFIG_DEFAULT_PRESETS)
    stats.preferences_count = dict_len(constants.CONFIG_PREFERENCES)

    mapping_rules = config.get(constants.CONFIG_MAPPING_RULES, None)
    if isinstance(mapping_rules, dict):
        rules = mapping_rules.get('rules', None)
        if isinstance(rules, list):
            stats.mapping_rule_count = len(rules)

    configuration = config.get(constants.CONFIG_CONFIGURATION, None)
    if isinstance(configuration, dict):
        service_config = configuration.get('service_config', None)
        if isinstance(service_config, dict):
            # only count services which actually have settings
            stats.service_config_count = len([
                service_name for service_name, service_settings in service_config.items()
                if service_settings
            ])
        service_enabled = configuration.get('service_enabled', None)
        if isinstance(service_enabled, dict):
            stats.service_enabled_count = len([
                service_name for service_name, enabled in service_enabled.items() if enabled
            ])
        user_uuid = configuration.get('user_uuid', None)
        if isinstance(user_uuid, str):
            stats.user_uuid = user_uuid
        stats.pro_api_key_set = bool(configuration.get('hypertts_pro_api_key', None))

    return stats


def detect_anomalies(previous: Optional[ConfigStats], current: ConfigStats) -> List[ConfigAnomaly]:
    """compare the configuration we are about to persist with the last known good one (the most
    recent backup) and flag anything which looks like data loss rather than a user action."""
    anomalies = []

    if previous == None:
        return anomalies

    # identity first: the anonymous user_uuid is written once on install and no screen ever removes
    # or changes it, so losing it is worth knowing about even when there was no user data at stake
    if previous.has_user_uuid() and not current.has_user_uuid():
        anomalies.append(ConfigAnomaly('user_uuid disappeared from the configuration',
            ANOMALY_SEVERITY_ERROR))
    elif previous.has_user_uuid() and not current.same_installation_as(previous):
        # a different user_uuid means the configuration was regenerated from scratch rather than
        # edited: it belongs to a fresh install, not to this one
        anomalies.append(ConfigAnomaly('user_uuid changed, the configuration was regenerated',
            ANOMALY_SEVERITY_ERROR))

    if previous.looks_empty():
        # nothing else was there to lose
        return anomalies

    if current.looks_empty() and not current.same_installation_as(previous):
        # every trace of the user's configuration is gone, and it doesn't even carry the user_uuid
        # of the configuration we last saw. this is not something the HyperTTS screens can produce,
        # it means the configuration we are holding is not the user's
        anomalies.append(ConfigAnomaly(
            f'configuration is empty, previously had {previous.describe()}',
            ANOMALY_SEVERITY_ERROR))
        # no point reporting every individual section as well
        return anomalies

    if previous.schema_version != None and current.schema_version == None:
        anomalies.append(ConfigAnomaly(
            f'config_schema disappeared from the configuration (was {previous.schema_version})',
            ANOMALY_SEVERITY_ERROR))
    elif (previous.schema_version != None and current.schema_version != None and
            current.schema_version < previous.schema_version):
        anomalies.append(ConfigAnomaly(
            f'config_schema went backwards, from {previous.schema_version} to {current.schema_version}',
            ANOMALY_SEVERITY_ERROR))

    # the following can be the result of a legitimate user action (deleting all presets, signing
    # out of HyperTTS Pro), so they are reported as warnings only
    if previous.preset_count > 0 and current.preset_count == 0:
        anomalies.append(ConfigAnomaly(
            f'all presets disappeared from the configuration (was {previous.preset_count})',
            ANOMALY_SEVERITY_WARNING))

    if previous.mapping_rule_count > 0 and current.mapping_rule_count == 0:
        anomalies.append(ConfigAnomaly(
            f'all preset rules disappeared from the configuration (was {previous.mapping_rule_count})',
            ANOMALY_SEVERITY_WARNING))

    if previous.pro_api_key_set and not current.pro_api_key_set:
        anomalies.append(ConfigAnomaly('HyperTTS Pro API key disappeared from the configuration',
            ANOMALY_SEVERITY_WARNING))

    if previous.service_config_count > 0 and current.service_config_count == 0:
        anomalies.append(ConfigAnomaly(
            f'all service configuration disappeared (was {previous.service_config_count} services)',
            ANOMALY_SEVERITY_WARNING))

    return anomalies


def config_hash(config) -> str:
    """stable hash of a configuration, used to avoid writing identical backups"""
    canonical = json.dumps(config, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def atomic_write_json(filepath: str, data) -> None:
    """write json to filepath without ever truncating an existing file: serialize into a temporary
    file in the same directory, flush it all the way to disk, then rename over the target."""
    directory = os.path.dirname(filepath)
    os.makedirs(directory, exist_ok=True)
    file_handle_id, temp_filepath = tempfile.mkstemp(
        prefix=f'.{os.path.basename(filepath)}.', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(file_handle_id, 'w', encoding='utf-8') as file_handle:
            json.dump(data, file_handle, ensure_ascii=False, indent=2, default=str)
            file_handle.write('\n')
            file_handle.flush()
            os.fsync(file_handle.fileno())
        os.replace(temp_filepath, filepath)
    except Exception:
        try:
            os.remove(temp_filepath)
        except OSError:
            pass
        raise


class ConfigBackupManager():
    """manages the rolling configuration backups in user_files/config_backup/"""

    def __init__(self, anki_utils):
        self.anki_utils = anki_utils

    # locations
    # =========

    def get_backup_dir(self) -> str:
        return os.path.join(self.anki_utils.get_user_files_dir(), constants.CONFIG_BACKUP_DIR_NAME)

    def get_meta_json_path(self) -> str:
        return os.path.join(self.anki_utils.get_addon_dir(), constants.ANKI_ADDON_META_FILENAME)

    # writing backups
    # ===============

    def get_backup_filename(self, timestamp: datetime.datetime) -> str:
        """timestamped filename, with a numeric suffix when several backups land within the same
        second. the suffix is zero padded so that sorting the filenames keeps sorting them by age."""
        base_name = timestamp.strftime('%Y%m%d_%H%M%S')
        candidate = (f'{constants.CONFIG_BACKUP_FILE_PREFIX}{base_name}'
            f'{constants.CONFIG_BACKUP_FILE_EXTENSION}')
        suffix = 0
        while os.path.exists(os.path.join(self.get_backup_dir(), candidate)):
            suffix += 1
            candidate = (f'{constants.CONFIG_BACKUP_FILE_PREFIX}{base_name}_{suffix:03d}'
                f'{constants.CONFIG_BACKUP_FILE_EXTENSION}')
        return candidate

    def save_backup(self, config) -> Optional[str]:
        """save a backup of the configuration. returns the filename written, or None if no backup
        was needed (identical to the latest backup) or possible. never raises."""
        try:
            return self._save_backup(config)
        except Exception as e:
            logger.error(f'could not save configuration backup: {e}', exc_info=True)
            self.anki_utils.report_config_anomaly(f'could not save configuration backup: {e}',
                ANOMALY_SEVERITY_ERROR, {})
            return None

    def _save_backup(self, config) -> Optional[str]:
        stats = analyze_config(config)
        if stats.looks_wiped():
            # never store an empty configuration, it would be useless to restore and it would push
            # a good backup out of the rolling window
            logger.warning('not saving configuration backup, configuration looks empty')
            return None

        new_hash = config_hash(config)
        latest_backup = self.get_latest_backup()
        if latest_backup != None and latest_backup.config_hash == new_hash:
            logger.debug('configuration unchanged since last backup, not saving a new one')
            return None

        timestamp = self.anki_utils.get_current_time()
        filename = self.get_backup_filename(timestamp)
        filepath = os.path.join(self.get_backup_dir(), filename)
        backup_data = {
            constants.CONFIG_BACKUP_KEY_METADATA: {
                'timestamp': timestamp.isoformat(),
                'hypertts_version': version.ANKI_HYPER_TTS_VERSION,
                'config_hash': new_hash,
                'stats': stats.as_dict()
            },
            constants.CONFIG_BACKUP_KEY_CONFIG: config
        }
        atomic_write_json(filepath, backup_data)
        logger.info(f'wrote configuration backup {filename} ({stats.describe()})')
        self.prune_backups()
        return filename

    def prune_backups(self) -> List[str]:
        """keep only the most recent constants.CONFIG_BACKUP_MAX_COUNT backups"""
        filenames = self.get_backup_filenames()
        removed = []
        for filename in filenames[constants.CONFIG_BACKUP_MAX_COUNT:]:
            filepath = os.path.join(self.get_backup_dir(), filename)
            try:
                os.remove(filepath)
                removed.append(filename)
            except OSError as e:
                logger.warning(f'could not remove old configuration backup {filename}: {e}')
        if len(removed) > 0:
            logger.debug(f'removed {len(removed)} old configuration backups')
        return removed

    # reading backups
    # ===============

    def get_backup_filenames(self) -> List[str]:
        """backup filenames, most recent first (the filename starts with a sortable timestamp)"""
        backup_dir = self.get_backup_dir()
        if not os.path.isdir(backup_dir):
            return []
        filenames = [
            filename for filename in os.listdir(backup_dir)
            if filename.startswith(constants.CONFIG_BACKUP_FILE_PREFIX) and
                filename.endswith(constants.CONFIG_BACKUP_FILE_EXTENSION)
        ]
        filenames.sort(reverse=True)
        return filenames

    def list_backups(self) -> List[ConfigBackupInfo]:
        """describe all backups on disk, most recent first. never raises."""
        return [self.get_backup_info(filename) for filename in self.get_backup_filenames()]

    def get_latest_backup(self) -> Optional[ConfigBackupInfo]:
        filenames = self.get_backup_filenames()
        if len(filenames) == 0:
            return None
        return self.get_backup_info(filenames[0])

    def get_latest_valid_backup(self) -> Optional[ConfigBackupInfo]:
        """the most recent backup which contains configuration worth restoring"""
        for backup_info in self.list_backups():
            if backup_info.looks_valid():
                return backup_info
        return None

    def get_latest_readable_backup(self) -> Optional[ConfigBackupInfo]:
        """the most recent backup we could parse, whether or not it contains any user data. this is
        the baseline for detecting data loss: comparing against the most recent *non empty* backup
        instead would keep flagging a configuration the user emptied on purpose."""
        for backup_info in self.list_backups():
            if backup_info.parse_error == None and backup_info.stats != None:
                return backup_info
        return None

    def get_backup_info(self, filename: str) -> ConfigBackupInfo:
        filepath = os.path.join(self.get_backup_dir(), filename)
        backup_info = ConfigBackupInfo(filename=filename, filepath=filepath)
        try:
            backup_info.size_bytes = os.path.getsize(filepath)
        except OSError as e:
            backup_info.parse_error = str(e)
            return backup_info
        try:
            config, metadata = self.read_backup_file(filepath)
        except errors.ConfigBackupError as e:
            backup_info.parse_error = e.error_message
            backup_info.timestamp = self.get_file_timestamp(filepath)
            return backup_info
        backup_info.stats = analyze_config(config)
        backup_info.config_hash = metadata.get('config_hash', None) or config_hash(config)
        backup_info.hypertts_version = metadata.get('hypertts_version', None)
        backup_info.timestamp = self.parse_timestamp(metadata.get('timestamp', None))
        if backup_info.timestamp == None:
            backup_info.timestamp = self.get_file_timestamp(filepath)
        return backup_info

    def read_backup_file(self, filepath: str):
        """returns (config, metadata). raises errors.ConfigBackupError if the file cannot be used."""
        filename = os.path.basename(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as file_handle:
                file_contents = file_handle.read()
        except OSError as e:
            raise errors.ConfigBackupError(filename, str(e))
        if len(file_contents.strip()) == 0:
            raise errors.ConfigBackupError(filename, 'file is empty')
        try:
            backup_data = json.loads(file_contents)
        except json.JSONDecodeError as e:
            raise errors.ConfigBackupError(filename, f'invalid JSON: {e}')
        if not isinstance(backup_data, dict):
            raise errors.ConfigBackupError(filename, 'file does not contain a JSON object')
        if constants.CONFIG_BACKUP_KEY_CONFIG in backup_data:
            config = backup_data[constants.CONFIG_BACKUP_KEY_CONFIG]
            metadata = backup_data.get(constants.CONFIG_BACKUP_KEY_METADATA, {})
            if not isinstance(metadata, dict):
                metadata = {}
        else:
            # tolerate a bare configuration dict, users may have copied one in by hand
            config = backup_data
            metadata = {}
        if not isinstance(config, dict):
            raise errors.ConfigBackupError(filename, 'configuration is not a JSON object')
        return config, metadata

    def load_backup_config(self, filename: str) -> Dict[str, Any]:
        """load the configuration stored in a backup, ready to be persisted. raises
        errors.ConfigBackupError if the backup cannot be used."""
        filepath = os.path.join(self.get_backup_dir(), filename)
        config, unused_metadata = self.read_backup_file(filepath)
        stats = analyze_config(config)
        if not stats.has_user_data():
            raise errors.ConfigBackupError(filename,
                'this backup does not contain any configuration to restore')
        return config

    def parse_timestamp(self, timestamp_str) -> Optional[datetime.datetime]:
        if not isinstance(timestamp_str, str):
            return None
        try:
            return datetime.datetime.fromisoformat(timestamp_str)
        except ValueError:
            return None

    def get_file_timestamp(self, filepath: str) -> Optional[datetime.datetime]:
        try:
            return datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
        except OSError:
            return None

    # configuration health checks
    # ===========================

    def check_config_before_write(self, config) -> bool:
        """called before the configuration is persisted. reports anomalies to sentry, and returns
        False if the write should be blocked because it would destroy the user's configuration.
        never raises."""
        try:
            return self._check_config_before_write(config)
        except Exception as e:
            logger.error(f'could not check configuration before write: {e}', exc_info=True)
            return True

    def _check_config_before_write(self, config) -> bool:
        current_stats = analyze_config(config)
        latest_backup = self.get_latest_readable_backup()
        previous_stats = latest_backup.stats if latest_backup != None else None

        anomalies = detect_anomalies(previous_stats, current_stats)
        for anomaly in anomalies:
            self.report_anomaly(anomaly, current_stats, previous_stats, latest_backup)

        if (current_stats.looks_empty() and previous_stats != None and
                previous_stats.has_user_data() and
                not current_stats.same_installation_as(previous_stats)):
            # we are about to replace a configuration which had presets/API keys with an empty one
            # which isn't even from this installation. this is the scenario described in issue #360:
            # refuse, so that the loss doesn't become permanent and the user can restore a backup.
            # a user deliberately deleting their last preset or removing their API key keeps their
            # user_uuid, so their save goes through as normal.
            logger.error('refusing to overwrite the configuration with an empty one')
            return False

        return True

    def report_anomaly(self, anomaly: ConfigAnomaly, current_stats: ConfigStats,
            previous_stats: Optional[ConfigStats], latest_backup: Optional[ConfigBackupInfo]) -> None:
        extra = {
            'current': current_stats.as_dict(),
            'previous': previous_stats.as_dict() if previous_stats != None else None,
            'latest_backup': latest_backup.filename if latest_backup != None else None,
            'backup_count': len(self.get_backup_filenames()),
            'meta_json': self.get_meta_json_status()
        }
        self.anki_utils.report_config_anomaly(anomaly.message, anomaly.severity, extra)

    def get_meta_json_status(self) -> Dict[str, Any]:
        """look at anki's meta.json (where our configuration really lives) without going through
        anki's API, which hides parse errors. this is our best forensic evidence for issue #360."""
        status = {
            'exists': False,
            'size': None,
            'parse_error': None,
            'has_config_key': None,
            'config_key_count': None
        }
        try:
            filepath = self.get_meta_json_path()
            if not os.path.isfile(filepath):
                return status
            status['exists'] = True
            status['size'] = os.path.getsize(filepath)
            with open(filepath, 'r', encoding='utf-8') as file_handle:
                meta_json = json.load(file_handle)
            if not isinstance(meta_json, dict):
                status['parse_error'] = 'meta.json does not contain a JSON object'
                return status
            addon_config = meta_json.get(constants.ANKI_ADDON_META_CONFIG_KEY, None)
            status['has_config_key'] = addon_config != None
            if isinstance(addon_config, dict):
                status['config_key_count'] = len(addon_config)
        except json.JSONDecodeError as e:
            status['parse_error'] = f'invalid JSON: {e}'
        except OSError as e:
            status['parse_error'] = f'could not read: {e}'
        except Exception as e:
            status['parse_error'] = str(e)
        return status

    def check_startup_config_state(self, config) -> bool:
        """called at startup, once the configuration has been loaded. reports anything which looks
        wrong to sentry. returns False if the configuration we loaded cannot be trusted, in which
        case the caller must not write it back. never raises."""
        try:
            return self._check_startup_config_state(config)
        except Exception as e:
            logger.error(f'could not check startup configuration state: {e}', exc_info=True)
            return True

    def _check_startup_config_state(self, config) -> bool:
        current_stats = analyze_config(config)
        meta_json_status = self.get_meta_json_status()
        logger.info(f'startup configuration: {current_stats.describe()}, '
            f'meta.json: {meta_json_status}')

        config_trusted = True

        if meta_json_status['parse_error'] != None:
            # anki couldn't parse meta.json either, so whatever we just loaded is the packaged
            # default configuration, not the user's. the damaged file is still on disk and may be
            # recoverable, we must not overwrite it.
            self.anki_utils.report_config_anomaly(
                f"""anki's meta.json could not be parsed: {meta_json_status['parse_error']}""",
                ANOMALY_SEVERITY_ERROR,
                {'meta_json': meta_json_status, 'current': current_stats.as_dict()})
            config_trusted = False

        if current_stats.looks_empty():
            latest_backup = self.get_latest_readable_backup()
            if (latest_backup != None and latest_backup.stats.has_user_data() and
                    not current_stats.same_installation_as(latest_backup.stats)):
                self.anki_utils.report_config_anomaly(
                    f'configuration is empty at startup, latest backup has '
                    f'{latest_backup.stats.describe()}',
                    ANOMALY_SEVERITY_ERROR,
                    {'meta_json': meta_json_status,
                     'current': current_stats.as_dict(),
                     'previous': latest_backup.stats.as_dict(),
                     'latest_backup': latest_backup.filename})
                config_trusted = False

        return config_trusted
