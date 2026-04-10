import json
import traceback

from . import constants

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
            return event
            
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
                            return event

    return None

# before_send_transaction
def filter_transactions(event, hint):
    operation = event.get('contexts', {}).get('trace', {}).get('op', None)
    if operation == 'audio':
        return event
    return None    
