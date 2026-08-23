import pytest

from hypertts_addon import constants
from hypertts_addon import logging_utils
from hypertts_addon import stats

from test_utils import testing_utils

logger = logging_utils.get_test_child_logger(__name__)


def build_stats_global(feature_flags_enabled):
    anki_utils = testing_utils.MockAnkiUtils({})
    # init_load kicks off load_background without a done callback, which MockAnkiUtils can only
    # handle by queueing it. we don't want it to run anyway, it publishes events over the network
    anki_utils.defer_background_tasks = True
    stats_global = stats.StatsGlobal(anki_utils, 'user_uuid_1', {}, False, False)

    def load_feature_flags():
        stats_global.feature_flags_enabled = feature_flags_enabled
        stats_global.feature_flags = {key: 'enabled' for key, enabled
            in feature_flags_enabled.items() if enabled}

    stats_global.load_feature_flags = load_feature_flags
    return stats_global


def test_init_load_enables_remote_logging_with_feature_flag(monkeypatch):
    """sentry-full-reporting opts a user into remote logging as well as full trace sampling"""
    # pytest tests/test_stats.py -k test_init_load_enables_remote_logging_with_feature_flag
    calls = []
    monkeypatch.setattr(logging_utils, 'enable_sentry_remote_logging', lambda: calls.append(True))

    stats_global = build_stats_global({constants.FEATURE_FLAG_SENTRY_FULL_REPORTING: True})
    stats_global.init_load()

    assert len(calls) == 1


def test_init_load_leaves_remote_logging_off_without_feature_flag(monkeypatch):
    # pytest tests/test_stats.py -k test_init_load_leaves_remote_logging_off_without_feature_flag
    calls = []
    monkeypatch.setattr(logging_utils, 'enable_sentry_remote_logging', lambda: calls.append(True))

    stats_global = build_stats_global({constants.FEATURE_FLAG_SENTRY_FULL_REPORTING: False})
    stats_global.init_load()
    assert len(calls) == 0

    # no flags at all (the flags request failed, or stats are disabled)
    stats_global = build_stats_global({})
    stats_global.init_load()
    assert len(calls) == 0
