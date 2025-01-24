import os
import json
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
            result = sentry_utils.sentry_filter(event, event.get('hint', {}))
            assert result is not None, f"Valid event {filename} was rejected"
            logger.info(f'confirmed valid exception accept {filepath}')

    # test events that should be rejected
    reject_events_dir = os.path.join('tests', 'test_data_sentry', 'reject_events')
    for filename in os.listdir(reject_events_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(reject_events_dir, filename)
            logger.info(f'loading invalid exception {filepath}')
            event = load_json_file(filepath)
            result = sentry_utils.sentry_filter(event, event.get('hint', {}))
            assert result is None, f"Invalid event {filename} was accepted"
            logger.info(f'confirmed invalid exception reject {filepath}')
