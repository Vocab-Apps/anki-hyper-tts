import sys
import os
import traceback
import logging
import uuid
import re
import pprint
import json

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
    from hypertts_addon import constants
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
    from . import config_models

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

    def save_configuration(configuration: config_models.Configuration) -> None:
        """
        Save the configuration to the addon config.
        """
        addon_config = aqt.mw.addonManager.getConfig(constants.CONFIG_ADDON_NAME)
        addon_config[constants.CONFIG_CONFIGURATION] = config_models.serialize_configuration(configuration)
        aqt.mw.addonManager.writeConfig(constants.CONFIG_ADDON_NAME, addon_config)

    configuration, first_install = get_configuration()
    save_configuration(configuration)

    # setup sentry crash reporting
    # ============================

    if hasattr(sys, '_sentry_crash_reporting'):
        # setup crash reporting
        # =====================

        from . import version
        from . import sentry_utils

        production_sample_rate = 0.025 if configuration.hypertts_pro_api_key_set() else 0.01
        traces_sample_rate_map = {
            'development': 1.0,
            'production': production_sample_rate
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
        sentry_sdk.set_user({"id": configuration.user_uuid})
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
        if configuration.enable_stats():
            # initialize stats global object
            sys._hypertts_stats_global = stats.StatsGlobal(ankiutils, 
                                                        configuration.user_uuid,
                                                        {
                                                            'hypertts_days_since_install': configuration.days_since_install(),
                                                            'hypertts_trial_registration_step': configuration.trial_registration_step.name,
                                                            'hypertts_pro': configuration.hypertts_pro_api_key_set()
                                                        },
                                                        first_install,
                                                        configuration.hypertts_pro_api_key_set()
                                                        )
