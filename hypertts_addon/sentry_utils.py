import json
import traceback

from . import constants


# Key: (user_id, group_key_tuple), Value: int count
_event_counts = {}

def reset_rate_limits():
    """Reset all rate limit counters. Used for testing."""
    _event_counts.clear()

def _compute_event_group_key(event):
    """Compute a hashable key identifying the exception group for rate limiting."""
    if 'exception' in event:
        values = event.get('exception', {}).get('values', [])
        if values:
            last_exc = values[-1]
            exc_type = last_exc.get('type', 'unknown')
            frames = last_exc.get('stacktrace', {}).get('frames', [])
            for frame in reversed(frames):
                filename = frame.get('filename', '')
                if ('hypertts_addon' in filename or
                    'anki-hyper-tts' in filename or
                    constants.ANKIWEB_ADDON_ID in filename):
                    return ('exception', exc_type, filename, frame.get('function', ''))
            return ('exception', exc_type)

    if 'logger' in event:
        logger_name = event.get('logger', '')
        extra = event.get('extra', {})
        log_location = extra.get('log_location', None)
        if log_location:
            return ('logger', logger_name,
                    log_location.get('filename', ''),
                    str(log_location.get('line_number', '')))
        else:
            return ('logger', logger_name,
                    event.get('message', event.get('logentry', {}).get('formatted', '')))

    return None

def _apply_rate_limit(event):
    """Drop the event if this user has already sent too many for this exception group."""
    user_id = event.get('user', {}).get('id', 'unknown')
    group_key = _compute_event_group_key(event)
    if group_key is None:
        return event

    rate_limit_key = (user_id, group_key)
    count = _event_counts.get(rate_limit_key, 0) + 1
    _event_counts[rate_limit_key] = count

    if count > constants.MAX_SENTRY_EVENTS_PER_USER_PER_GROUP:
        return None
    return event

def sentry_filter_dump_json(event, hint):
    with open('/home/luc/code/python/anki-hyper-tts/temp/exception.json', 'w') as f:
        json.dump(event, f, indent=4)
        f.flush()
    with open('/home/luc/code/python/anki-hyper-tts/temp/hint.json', 'w') as f:
        json.dump(hint, f, indent=4)
        f.flush()
    return event

# this is the implementation of the before_send function
def sentry_filter(event, hint):

    # if no exception info, check if event is from our module
    if 'logger' in event:
        logger_name = event.get('logger', '')
        if logger_name.startswith('hypertts'):
            # Group log-based events by call site (file + line) instead of message content
            # This prevents f-string messages with different variable values from creating separate issues
            extra = event.get('extra', {})
            log_location = extra.get('log_location', None)
            if log_location:
                event['fingerprint'] = [
                    logger_name,
                    log_location.get('filename', ''),
                    str(log_location.get('line_number', ''))
                ]
            return _apply_rate_limit(event)

    # check if there's an exception object directly in the event
    if 'exception' in event:
        exception = event.get('exception', {})
        values = exception.get('values', [])
        if values:
            for value in values:
                frames = value.get('stacktrace', {}).get('frames', [])
                for frame in frames:
                    filename = frame.get('filename', '')
                    if ('anki-hyper-tts' in filename or
                        constants.ANKIWEB_ADDON_ID in filename or
                        'hypertts_addon' in filename):
                            return _apply_rate_limit(event)

    return None

# before_send_transaction
def filter_transactions(event, hint):
    operation = event.get('contexts', {}).get('trace', {}).get('op', None)
    if operation == 'audio':
        return event
    return None    
