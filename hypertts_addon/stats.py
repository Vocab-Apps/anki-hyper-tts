import sys
import os
import requests
import json
import functools
import anki

from . import constants
from . import constants_events
from . import logging_utils
from . import version
logger = logging_utils.get_child_logger(__name__)

class StatsGlobal:
    CAPTURE_URL = "https://st.vocab.ai/capture/"

    def __init__(self, anki_utils, user_uuid, user_properties):
        self.anki_utils = anki_utils
        self.api_key = os.environ.get('STATS_API_KEY', 'phc_c9ijDJMNO8n7kzxPNlxwuiKIAlNcYhzeq7pa6aQYq9G')
        self.user_uuid = user_uuid
        self.user_properties = user_properties

    def publish(self, 
                context: constants_events.EventContext, 
                event: constants_events.Event,
                event_mode: constants_events.EventMode,
                event_properties: dict):
        logger.debug('publish')
        def get_publish_lambda(context: constants_events.EventContext, event: constants_events.Event,
                               event_mode: constants_events.EventMode,
                               event_properties: dict):
            def publish():
                self.publish_event(context, event, event_mode, event_properties)
            return publish
        self.anki_utils.run_in_background(get_publish_lambda(context, event, event_mode, event_properties), None)

    def construct_event_name(self, context: constants_events.EventContext, event: constants_events.Event):
        return f'{constants_events.PREFIX}:{constants_events.ADDON}:{context.name}:{event.name}'

    def publish_event(self, 
                context: constants_events.EventContext, 
                event: constants_events.Event,
                event_mode: constants_events.EventMode,
                event_properties: dict):
        logger.debug('publishing event')
        # in background thread
        headers = {
            "Content-Type": "application/json"
        }
        if event_mode:
            event_properties['mode'] = event_mode.name
        payload = {
            "api_key": self.api_key,
            "event": self.construct_event_name(context, event),
            "distinct_id": self.user_uuid,
            "properties": event_properties,
        }
        # for global events, add additional properties
        if context == constants_events.EventContext.addon:
            payload['properties']['hypertts_addon_version'] = version.ANKI_HYPER_TTS_VERSION
            payload['properties']['anki_version'] = anki.version
            payload['properties']['$set'] = {
                'anki_version': anki.version,
                'hypertts_addon_version': version.ANKI_HYPER_TTS_VERSION,
                'hypertts_addon_user': True,
                **self.user_properties
            }
        try:
            response = requests.post(self.CAPTURE_URL, 
                    headers=headers, 
                    data=json.dumps(payload), 
                    timeout=constants.RequestTimeoutShort)
            logger.debug(f'sent event: {context}:{event} ({event_mode}), status: {response.status_code}')
        except Exception as e:
            logger.warning(f'could not send event: {context}:{event} ({event_mode}): {e}')

def event_global(event: constants_events.Event):
    if hasattr(sys, '_hypertts_stats_global'):
        sys._hypertts_stats_global.publish(constants_events.EventContext.addon, event, None, {})

def send_event(context: constants_events.EventContext, event: constants_events.Event, event_mode: constants_events.EventMode,
               event_properties: dict):
    if hasattr(sys, '_hypertts_stats_global'):
        sys._hypertts_stats_global.publish(context, event, event_mode, event_properties)

def send_event_bg(context: constants_events.EventContext, event: constants_events.Event, event_mode: constants_events.EventMode,
               event_properties: dict):
    # we are already in the background thread
    if hasattr(sys, '_hypertts_stats_global'):
        sys._hypertts_stats_global.publish_event(context, event, event_mode, event_properties)

class StatsEvent:
    def __init__(self, 
                 context: constants_events.EventContext, 
                 event: constants_events.Event,
                 event_mode: constants_events.EventMode):
        self.context = context
        self.event = event
        self.event_mode = event_mode

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            send_event(self.context, self.event, self.event_mode, {})
            return func(*args, **kwargs)
        return wrapper

class StatsContext:

    def __init__(self, context: constants_events.EventContext):
        self.context = context

    def event(self, event: constants_events.Event, event_mode: constants_events.EventMode = None):
        return StatsEvent(self.context, event, event_mode)

    def send_event(self, event: constants_events.Event, event_mode: constants_events.EventMode = None,
                   properties: dict = {}):
        send_event(self.context, event, event_mode, properties)

