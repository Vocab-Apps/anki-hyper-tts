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
    # First check - reject events from ankihub logger
    if 'logger' in event and event.get('logger', '').startswith('ankihub'):
        return None

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

        return event
    
    # if no exception info, check if event is from our module
    if 'logger' in event:
        logger_name = event.get('logger', '')
        if logger_name.startswith('hypertts'):
            return event
            
    # check breadcrumbs categories
    if 'breadcrumbs' in event:
        breadcrumbs = event.get('breadcrumbs', {}).get('values', [])
        for crumb in breadcrumbs:
            category = crumb.get('category', '')
            if category.startswith('hypertts'):
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
                        constants.ANKIWEB_ADDON_ID in filename):
                        if 'ankihub' not in filename.lower():
                            return event

    return None

# before_send_transaction
def filter_transactions(event, hint):
    operation = event.get('contexts', {}).get('trace', {}).get('op', None)
    if operation == 'audio':
        return event
    return None    
