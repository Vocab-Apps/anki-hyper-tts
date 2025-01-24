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

    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']

        # do we recognize the paths in this stack trace ?
        relevant_exception = False
        stack_summary = traceback.extract_tb(tb)
        for stack_frame in stack_summary:
            filename = stack_frame.filename
            if 'anki-hyper-tts' in filename or constants.ANKIWEB_ADDON_ID in filename:
                relevant_exception = True
        
        # if not, discard
        if not relevant_exception:
            return None

    return event

# before_send_transaction
def filter_transactions(event, hint):
    operation = event.get('contexts', {}).get('trace', {}).get('op', None)
    if operation == 'audio':
        return event
    return None    