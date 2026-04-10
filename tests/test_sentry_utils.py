import os
import json
import pprint
import pytest

from hypertts_addon import sentry_utils
from hypertts_addon import logging_utils

logger = logging_utils.get_test_child_logger(__name__)

def load_json_file(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def test_sentry_filter():
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
