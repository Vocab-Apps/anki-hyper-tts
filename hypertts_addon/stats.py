import sys
import requests
import json
import functools

from . import constants_events
from . import logging_utils
logger = logging_utils.get_child_logger(__name__)

class StatsGlobal:
    CAPTURE_URL = "https://st.vocab.ai/capture/"

    def __init__(self, anki_utils, api_key, user_uuid):
        self.anki_utils = anki_utils
        self.api_key = api_key
        self.user_uuid = user_uuid

    def publish(self, context: constants_events.EventContext, event: constants_events.Event):
        logger.debug('publish')
        def get_publish_lambda(context: constants_events.EventContext, event: constants_events.Event):
            def publish():
                self.publish_event(context, event)
            return publish
        self.anki_utils.run_in_background(get_publish_lambda(context, event), None)

    def construct_event_name(self, context: constants_events.EventContext, event: constants_events.Event):
        return f'{constants_events.PREFIX}:{constants_events.ADDON}:{context.name}:{event.name}'

    def publish_event(self, context: constants_events.EventContext, event: constants_events.Event):
        logger.debug('publishing event')
        # in background thread
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "api_key": self.api_key,
            "event": self.construct_event_name(context, event),
            "distinct_id": self.user_uuid,
            "properties": {
            },
        }
        response = requests.post(self.CAPTURE_URL, headers=headers, data=json.dumps(payload))
        logger.debug(f'sent event: {context}:{event}, status: {response.status_code}')
        # print(response)        

def event_global(event: constants_events.Event):
    sys._hypertts_stats_global.publish(constants_events.EventContext.addon, event)

class StatsEvent:
    def __init__(self, context: constants_events.EventContext, event: constants_events.Event):
        self.context = context
        self.event = event

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            sys._hypertts_stats_global.publish(self.context, self.event)
            return func(*args, **kwargs)
        return wrapper

class StatsContext:

    def __init__(self, context: constants_events.EventContext):
        self.context = context

    def event(self, event: str):
        return StatsEvent(self.context, event)

