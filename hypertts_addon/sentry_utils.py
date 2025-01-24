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
    # check if we have exception info
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']

        # do we recognize the paths in this stack trace ?
        stack_summary = traceback.extract_tb(tb)
        
        # must have at least one frame from our code
        relevant_exception = False
        for stack_frame in stack_summary:
            filename = stack_frame.filename
            # check if from our addon code
            if ('anki-hyper-tts' in filename or 
                constants.ANKIWEB_ADDON_ID in filename):
                # but exclude certain paths
                if 'ankihub' not in filename.lower():
                    relevant_exception = True
                    break
        
        # if not from our code, discard
        if not relevant_exception:
            return None
    
    # if no exception info, check if event is from our module
    elif 'logger' in event:
        logger_name = event.get('logger', '')
        if not (logger_name.startswith('hypertts') or 
                'anki-hyper-tts' in logger_name or
                constants.ANKIWEB_ADDON_ID in logger_name):
            return None
    else:
        return None

    return event

# before_send_transaction
def filter_transactions(event, hint):
    operation = event.get('contexts', {}).get('trace', {}).get('op', None)
    if operation == 'audio':
        return event
    return None    
