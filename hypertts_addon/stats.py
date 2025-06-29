import sys
import os
import requests
import json
import functools
import anki
import pprint

from . import constants
from . import constants_events
from . import logging_utils
from . import version
logger = logging_utils.get_child_logger(__name__)

class StatsGlobal:
    BASE_URL = "https://st.vocab.ai"
    CAPTURE_URL = f"{BASE_URL}/capture/"

    def __init__(self, anki_utils, user_uuid, user_properties):
        self.anki_utils = anki_utils
        self.api_key = os.environ.get('STATS_API_KEY', 'phc_c9ijDJMNO8n7kzxPNlxwuiKIAlNcYhzeq7pa6aQYq9G')
        self.user_uuid = user_uuid
        self.user_properties = user_properties
        self.feature_flags = {}
        self.feature_flags_enabled = {}

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
        if event_mode:
            event_properties['mode'] = event_mode.name
        
        # for global events, add additional properties
        if context == constants_events.EventContext.addon:
            event_properties['hypertts_addon_version'] = version.ANKI_HYPER_TTS_VERSION
            event_properties['anki_version'] = anki.version
            event_properties['$set'] = {
                'anki_version': anki.version,
                'hypertts_addon_version': version.ANKI_HYPER_TTS_VERSION,
                'hypertts_addon_user': True,
                **self.user_properties
            }
        
        # Add feature flags if needed for this event context
        if self.should_include_feature_flags(context, event):
            for flag_key, flag_value in self.feature_flags.items():
                if self.feature_flags_enabled.get(flag_key, False):
                    event_properties[f'$feature/{flag_key}'] = flag_value
        
        event_name = self.construct_event_name(context, event)
        self.publish_posthog_event(event_name, event_properties)
    
    def publish_posthog_event(self, event_name: str, event_properties: dict):
        """
        Publish a standard PostHog event (e.g., $feature_flag_called).
        This method sends events directly without the custom prefix.
        """
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "api_key": self.api_key,
            "event": event_name,
            "distinct_id": self.user_uuid,
            "properties": event_properties,
        }
        try:
            logger.debug(f'sending posthog event: {event_name}, properties: {pprint.pformat(event_properties)}')
            response = requests.post(self.CAPTURE_URL, 
                    headers=headers, 
                    data=json.dumps(payload), 
                    timeout=constants.RequestTimeoutShort)
            logger.debug(f'sent posthog event: {event_name}, status: {response.status_code}')
        except Exception as e:
            logger.warning(f'could not send posthog event: {event_name}: {e}')

    def load_feature_flags(self):
        """
        Load all feature flags from PostHog REST API and store them in self.feature_flags.
        only supports multivariate flags which default to 'control'
        """
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "api_key": self.api_key,
                "distinct_id": self.user_uuid
            }
            
            response = requests.post(
                f"{self.BASE_URL}/flags?v=2",
                headers=headers,
                data=json.dumps(payload),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.debug(f'Feature flags API response: \n{pprint.pformat(data)}')
                flags = data.get('flags', {})
                # Store feature flags with their variant values
                self.feature_flags = {}
                self.feature_flags_enabled = {}
                for flag_key, flag_data in flags.items():
                    is_enabled = flag_data.get('enabled', False)
                    self.feature_flags_enabled[flag_key] = is_enabled
                    
                    if is_enabled:
                        # Use variant if available, otherwise use string representation of enabled state
                        variant = flag_data.get('variant')
                        if variant is not None:
                            self.feature_flags[flag_key] = str(variant)
                        else:
                            self.feature_flags[flag_key] = 'enabled'
                    else:
                        self.feature_flags[flag_key] = constants_events.FEATURE_FLAG_DEFAULT_VALUE
                logger.debug(f'Loaded {len(self.feature_flags)} feature flags: '
                             f'{pprint.pformat(self.feature_flags)} enabled: {pprint.pformat(self.feature_flags_enabled)}')
                
                # Report $feature_flag_called for each enabled feature flag
                for flag_key, is_enabled in self.feature_flags_enabled.items():
                    if is_enabled:
                        self.publish_posthog_event('$feature_flag_called', {
                            '$feature_flag': flag_key,
                            '$feature_flag_response': self.feature_flags.get(flag_key)
                        })
            else:
                logger.warning(f'Feature flags API returned status {response.status_code}')
                self.feature_flags = {}
                self.feature_flags_enabled = {}
                
        except Exception as e:
            logger.error(f'Error loading feature flags: {e}')
            self.feature_flags = {}
            self.feature_flags_enabled = {}
    
    def get_feature_flag_value(self, flag_key: str) -> str:
        """
        Get the value of a feature flag.
        
        Args:
            flag_key: The key of the feature flag
            
        Returns:
            The variant value of the feature flag, or constants_events.FEATURE_FLAG_DEFAULT_VALUE if not found
        """
        return self.feature_flags.get(flag_key, constants_events.FEATURE_FLAG_DEFAULT_VALUE)

    def get_feature_flag_enabled(self, flag_key: str) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag_key: The key of the feature flag
            
        Returns:
            True if the feature flag is enabled, False otherwise
        """
        return self.feature_flags_enabled.get(flag_key, False)
    
    def should_include_feature_flags(self, event_context: constants_events.EventContext, event: constants_events.Event) -> bool:
        """
        Determine if feature flags should be included for this event.
        
        Args:
            event_context: The context of the event
            event: The event type
            
        Returns:
            True if feature flags should be included, False otherwise
        """
        return event_context in [constants_events.EventContext.addon, constants_events.EventContext.trial_signup]
    
    def init_load_background(self):
        """
        Load feature flags in the background thread.
        """
        self.anki_utils.run_in_background(self.load_feature_flags, None)

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

def feature_flag_enabled(flag_key: str):
    # check if stats are enabled, default to False
    if hasattr(sys, '_hypertts_stats_global'):
        return sys._hypertts_stats_global.get_feature_flag_enabled(flag_key)
    return False

def feature_flag_value(flag_key: str) -> str:
    # check if stats are enabled, default to control
    if hasattr(sys, '_hypertts_stats_global'):
        return sys._hypertts_stats_global.get_feature_flag_value(flag_key)
    return constants_events.FEATURE_FLAG_DEFAULT_VALUE