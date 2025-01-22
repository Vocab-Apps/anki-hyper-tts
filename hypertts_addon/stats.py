import sys
import requests
import json
import functools

from . import logging_utils
logger = logging_utils.get_child_logger(__name__)

class StatsGlobal:
    CAPTURE_URL = "https://st.vocab.ai/capture/"

    def __init__(self, anki_utils, api_key, user_uuid):
        self.anki_utils = anki_utils
        self.api_key = api_key
        self.user_uuid = user_uuid

    def publish(self, context: str, event: str):
        logger.debug('publish')
        def get_publish_lambda(context: str, event: str):
            def publish():
                self.publish_event(context, event)
            return publish
        self.anki_utils.run_in_background(get_publish_lambda(context, event), None)

    def construct_event_name(self, context: str, event: str):
        return f'anki_addon_v1:hypertts:{context}:{event}'

    def publish_event(self, context: str, event: str):
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

def event_global(event: str):
    sys._hypertts_stats_global.publish('global', event)

class StatsEvent:
    def __init__(self, context: str, event: str):
        self.context = context
        self.event = event

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            sys._hypertts_stats_global.publish(self.context, self.event)
            return func(*args, **kwargs)
        return wrapper

class StatsContext:

    def __init__(self, context_str):
        self.context_str = context_str

    def event(self, event: str):
        return StatsEvent(self.context_str, event)

