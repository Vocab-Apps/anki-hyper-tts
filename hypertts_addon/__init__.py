import sys
import os
import traceback
import logging
import uuid
import re
import pprint
import json

from hypertts_addon import constants
from hypertts_addon import config_models

def get_configuration_dict() -> dict:
    """
    return the `configuration` key of the addon config.
    """
    addon_config = aqt.mw.addonManager.getConfig(constants.CONFIG_ADDON_NAME)
    config_configuration = addon_config.get(constants.CONFIG_CONFIGURATION, {})
    return config_configuration

def generate_user_uuid() -> str:
    """
    Generate a new user UUID.
    """
    return uuid.uuid4().hex

def get_configuration() -> tuple[config_models.Configuration, bool]:
    """
    Returns the configuration for the addon, in config_models.Configuration type.
    """
    config_dict: dict = get_configuration_dict()
    config: config_models.Configuration = config_models.deserialize_configuration(config_dict)
    first_install = False
    if config.user_uuid == None:
        # first install
        first_install = True
        config.user_uuid = generate_user_uuid()
        # enable welcome messages and features
        config.new_install_settings()

    return config, first_install

if hasattr(sys, '_pytest_mode'):
    # called from within a test run
    pass
else:
    # configure imports
    # =================

    # running from within Anki
    import anki
    import anki.hooks
    import aqt
    import anki.sound

    # need to declare upfront whether we're doing crash reporting
    # ============================================================
    addon_config = aqt.mw.addonManager.getConfig(constants.CONFIG_ADDON_NAME)
    enable_stats_error_reporting = addon_config.get(constants.CONFIG_PREFERENCES, {}).\
        get('error_handling', {}).get('error_stats_reporting', True)
    if constants.ENABLE_SENTRY_CRASH_REPORTING and enable_stats_error_reporting:
        import sentry_sdk        
        # check version. some anki addons package an obsolete version of sentry_sdk
        sentry_sdk_int_version = int(sentry_sdk.VERSION.replace('.', ''))
        if sentry_sdk_int_version >= 155:        
            sys._sentry_crash_reporting = True

    # setup logger
    # ============

    from . import logging_utils

    if os.environ.get('HYPER_TTS_DEBUG_LOGGING', '') == 'enable':
        # log everything to stdout
        logging_utils.configure_console_logging()
    elif os.environ.get('HYPER_TTS_DEBUG_LOGGING', '') == 'file':
        # log everything to file
        logging_utils.configure_file_logging(os.environ['HYPER_TTS_DEBUG_LOGFILE'])
    else:
        # log at info level, but with null handler, so that sentry picks up breadcrumbs and errors
        logging_utils.configure_silent()

    logger = logging_utils.get_child_logger(__name__)

    # anonymous user id
    # =================

    # for new installs
    # - create the user_uuid
    # - enable all help screens
    # for existing installs
    # - default help screens to off

    # get or create user_uuid
    first_install = False
    config_configuration = addon_config.get(constants.CONFIG_CONFIGURATION, {})
    user_uuid = config_configuration.get('user_uuid', None)
    if user_uuid != None:
        user_id = user_uuid
    else:
        user_uuid = uuid.uuid4().hex
        config_configuration['user_uuid'] = user_uuid
        # first install, display introduction message, but not for existing users
        config_configuration['display_introduction_message'] = True
        addon_config[constants.CONFIG_CONFIGURATION] = config_configuration
        aqt.mw.addonManager.writeConfig(constants.CONFIG_ADDON_NAME, addon_config)
        user_id = user_uuid
        # check if legacy unique_id exists
        if 'unique_id' not in addon_config:
            first_install = True

    # setup sentry crash reporting
    # ============================

    if hasattr(sys, '_sentry_crash_reporting'):
        # setup crash reporting
        # =====================

        from . import version
        from . import sentry_utils

        traces_sample_rate_map = {
            'development': 1.0,
            'production': 0.021
        }

        # need to create an anki-hyper-tts project in sentry.io first
        sentry_env = os.environ.get('SENTRY_ENV', 'production')
        sentry_sdk.init(
            "https://a4170596966d47bb9f8fda74a9370bc7@o968582.ingest.sentry.io/6170140",
            traces_sample_rate=traces_sample_rate_map[sentry_env],
            release=f'anki-hyper-tts@{version.ANKI_HYPER_TTS_VERSION}',
            environment=sentry_env,
            before_send=sentry_utils.sentry_filter,
            before_send_transaction=sentry_utils.filter_transactions
        )
        sentry_sdk.set_user({"id": user_id})
        sentry_sdk.set_tag("anki_version", anki.version)
    else:
        logger.info(f'disabling crash reporting')

    # addon imports
    # =============

    from . import anki_utils
    from . import servicemanager
    from . import hypertts
    from . import gui

    # initialize hypertts
    # ===================

    ankiutils = anki_utils.AnkiUtils()

    def services_dir():
        current_script_path = os.path.realpath(__file__)
        current_script_dir = os.path.dirname(current_script_path)
        return os.path.join(current_script_dir, 'services')
    service_manager = servicemanager.ServiceManager(services_dir(), f'{constants.DIR_HYPERTTS_ADDON}.{constants.DIR_SERVICES}', False)
    service_manager.init_services()
    hyper_tts = hypertts.HyperTTS(ankiutils, service_manager)
    # configure services based on config
    with hyper_tts.error_manager.get_single_action_context('Configuring Services'):
        service_manager.configure(hyper_tts.get_configuration())
    gui.init(hyper_tts)


    # stats
    from . import stats
    from . import constants_events
    if not hasattr(sys, '_pytest_mode') and enable_stats_error_reporting:
        sys._hypertts_stats_global = stats.StatsGlobal(ankiutils, user_uuid)
        stats.event_global(constants_events.Event.open)
        if first_install:
            stats.event_global(constants_events.Event.install)
