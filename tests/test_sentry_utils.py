import os
import json
import pprint
import pytest

from hypertts_addon import constants
from hypertts_addon import sentry_utils
from hypertts_addon import logging_utils

logger = logging_utils.get_test_child_logger(__name__)

def load_json_file(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def test_sentry_filter():
    sentry_utils.reset_rate_limits()
    # test valid events
    valid_events_dir = os.path.join('tests', 'test_data_sentry', 'valid_events')
    for filename in os.listdir(valid_events_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(valid_events_dir, filename)
            logger.info(f'loading valid exception {filepath}')
            event = load_json_file(filepath)
            logger.debug(f'valid exception content: {pprint.pformat(event)}')
            result = sentry_utils.sentry_filter(event, {})
            assert result is not None, f"Valid event {filename} was rejected"
            logger.info(f'confirmed valid exception accept {filepath}')

    # test that logger events with log_location get fingerprinted by call site
    logger_event_with_location = {
        'logger': 'hypertts.service_windows',
        'message': 'unknown language: unknown, could not process voice [Microsoft Harri Online]',
        'extra': {
            'log_location': {
                'filename': 'service_windows.py',
                'line_number': 336
            }
        }
    }
    result = sentry_utils.sentry_filter(logger_event_with_location, {})
    assert result is not None
    assert result['fingerprint'] == ['hypertts.service_windows', 'service_windows.py', '336']

    # a different message from the same call site should produce the same fingerprint
    logger_event_with_location_2 = {
        'logger': 'hypertts.service_windows',
        'message': 'unknown language: unknown, could not process voice [Microsoft Ximena Online]',
        'extra': {
            'log_location': {
                'filename': 'service_windows.py',
                'line_number': 336
            }
        }
    }
    result_2 = sentry_utils.sentry_filter(logger_event_with_location_2, {})
    assert result_2 is not None
    assert result_2['fingerprint'] == result['fingerprint']

    # logger events without log_location should not get a fingerprint
    logger_event_no_location = {
        'logger': 'hypertts.servicemanager',
        'message': 'some info message',
    }
    result_3 = sentry_utils.sentry_filter(logger_event_no_location, {})
    assert result_3 is not None
    assert 'fingerprint' not in result_3

    # test events that should be rejected
    reject_events_dir = os.path.join('tests', 'test_data_sentry', 'reject_events')
    for filename in os.listdir(reject_events_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(reject_events_dir, filename)
            logger.info(f'loading invalid exception {filepath}')
            event = load_json_file(filepath)
            logger.debug(f'invalid exception content: {pprint.pformat(event)}')
            result = sentry_utils.sentry_filter(event, {})
            assert result is None, f"Invalid event {filename} was accepted"
            logger.info(f'confirmed invalid exception reject {filepath}')


def _make_exception_event(user_id, exc_type, filename, function):
    """Helper to build a minimal exception event for rate limit tests."""
    return {
        'user': {'id': user_id},
        'exception': {
            'values': [{
                'type': exc_type,
                'value': f'test {exc_type}',
                'stacktrace': {
                    'frames': [{
                        'filename': filename,
                        'function': function,
                        'lineno': 42,
                    }]
                }
            }]
        }
    }


def _make_logger_event(user_id, logger_name, message, log_location=None):
    """Helper to build a minimal logger event for rate limit tests."""
    event = {
        'user': {'id': user_id},
        'logger': logger_name,
        'message': message,
    }
    if log_location:
        event['extra'] = {'log_location': log_location}
    return event


def test_exception_rate_limit_basic():
    """Same exception event sent MAX+1 times: first MAX accepted, next dropped."""
    sentry_utils.reset_rate_limits()
    limit = constants.MAX_SENTRY_EVENTS_PER_USER_PER_GROUP
    event = _make_exception_event('user_a', 'AudioNotFoundError',
                                  'hypertts_addon/services/service_duden.py', 'get_tts_audio')
    for i in range(limit):
        result = sentry_utils.sentry_filter(event, {})
        assert result is not None, f"Event {i+1} should be accepted"
    result = sentry_utils.sentry_filter(event, {})
    assert result is None, f"Event {limit+1} should be dropped"


def test_exception_rate_limit_different_types():
    """Different exception types are tracked independently."""
    sentry_utils.reset_rate_limits()
    limit = constants.MAX_SENTRY_EVENTS_PER_USER_PER_GROUP
    event_a = _make_exception_event('user_a', 'RuntimeError',
                                    'hypertts_addon/gui.py', 'launch')
    event_b = _make_exception_event('user_a', 'AudioNotFoundError',
                                    'hypertts_addon/gui.py', 'launch')
    for i in range(limit):
        assert sentry_utils.sentry_filter(event_a, {}) is not None
    # RuntimeError exhausted, but AudioNotFoundError still available
    assert sentry_utils.sentry_filter(event_a, {}) is None
    assert sentry_utils.sentry_filter(event_b, {}) is not None


def test_exception_rate_limit_different_users():
    """Different users are tracked independently."""
    sentry_utils.reset_rate_limits()
    limit = constants.MAX_SENTRY_EVENTS_PER_USER_PER_GROUP
    event_a = _make_exception_event('user_a', 'RuntimeError',
                                    'hypertts_addon/gui.py', 'launch')
    event_b = _make_exception_event('user_b', 'RuntimeError',
                                    'hypertts_addon/gui.py', 'launch')
    for i in range(limit):
        assert sentry_utils.sentry_filter(event_a, {}) is not None
    # user_a exhausted
    assert sentry_utils.sentry_filter(event_a, {}) is None
    # user_b still has quota
    for i in range(limit):
        assert sentry_utils.sentry_filter(event_b, {}) is not None
    assert sentry_utils.sentry_filter(event_b, {}) is None


def test_logger_rate_limit():
    """Logger events with log_location are rate-limited at MAX_SENTRY_EVENTS_PER_USER_PER_GROUP."""
    sentry_utils.reset_rate_limits()
    limit = constants.MAX_SENTRY_EVENTS_PER_USER_PER_GROUP
    event = _make_logger_event('user_a', 'hypertts.service_azure',
                               'status code 429: Too Many Requests',
                               log_location={'filename': 'service_azure.py', 'line_number': 134})
    for i in range(limit):
        result = sentry_utils.sentry_filter(event, {})
        assert result is not None, f"Logger event {i+1} should be accepted"
    assert sentry_utils.sentry_filter(event, {}) is None, f"Logger event {limit+1} should be dropped"


def test_rate_limit_different_locations():
    """Same exception type from different code locations tracked separately."""
    sentry_utils.reset_rate_limits()
    limit = constants.MAX_SENTRY_EVENTS_PER_USER_PER_GROUP
    event_a = _make_exception_event('user_a', 'RuntimeError',
                                    'hypertts_addon/services/service_azure.py', 'get_audio')
    event_b = _make_exception_event('user_a', 'RuntimeError',
                                    'hypertts_addon/services/service_duden.py', 'get_audio')
    for i in range(limit):
        assert sentry_utils.sentry_filter(event_a, {}) is not None
    assert sentry_utils.sentry_filter(event_a, {}) is None
    # Different location still has quota
    for i in range(limit):
        assert sentry_utils.sentry_filter(event_b, {}) is not None
    assert sentry_utils.sentry_filter(event_b, {}) is None


def test_rate_limit_reset():
    """reset_rate_limits() clears counters, allowing MAX more."""
    sentry_utils.reset_rate_limits()
    limit = constants.MAX_SENTRY_EVENTS_PER_USER_PER_GROUP
    event = _make_exception_event('user_a', 'RuntimeError',
                                  'hypertts_addon/gui.py', 'launch')
    for i in range(limit):
        assert sentry_utils.sentry_filter(event, {}) is not None
    assert sentry_utils.sentry_filter(event, {}) is None

    sentry_utils.reset_rate_limits()
    for i in range(limit):
        assert sentry_utils.sentry_filter(event, {}) is not None
    assert sentry_utils.sentry_filter(event, {}) is None


def test_rate_limit_with_real_event():
    """Load runtime_error.json and verify rate limiting with real event data."""
    sentry_utils.reset_rate_limits()
    limit = constants.MAX_SENTRY_EVENTS_PER_USER_PER_GROUP
    filepath = os.path.join('tests', 'test_data_sentry', 'valid_events', 'runtime_error.json')
    event = load_json_file(filepath)
    for i in range(limit):
        result = sentry_utils.sentry_filter(event, {})
        assert result is not None, f"Real event {i+1} should be accepted"
    result = sentry_utils.sentry_filter(event, {})
    assert result is None, f"Real event {limit+1} should be dropped"


def test_traces_sampler_uses_base_rate_when_flag_disabled(monkeypatch):
    monkeypatch.setattr('hypertts_addon.stats.feature_flag_enabled', lambda key: False)
    sampler = sentry_utils.make_traces_sampler(0.01)
    assert sampler({}) == 0.01


def test_traces_sampler_returns_full_when_flag_enabled(monkeypatch):
    captured = []
    def fake_flag(key):
        captured.append(key)
        return True
    monkeypatch.setattr('hypertts_addon.stats.feature_flag_enabled', fake_flag)
    sampler = sentry_utils.make_traces_sampler(0.01)
    assert sampler({}) == 1.0
    assert captured == ['sentry-full-reporting']
