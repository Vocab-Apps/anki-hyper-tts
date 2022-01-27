import sys
import os
import traceback
import logging
import re

if hasattr(sys, '_pytest_mode'):
    # called from within a test run
    pass
else:
    # configure imports
    # =================
    # we need to import internal modules in a particular way which differs whether we're running within anki or pytest
    sys._addon_import_level_base = 1
    sys._addon_import_level_services = 2

    # running from within Anki
    import anki
    import anki.hooks
    import aqt
    import anki.sound
    from . import constants
    from . import anki_utils
    from . import servicemanager
    from . import hypertts
    from . import gui
    
    # setup sentry crash reporting
    # ============================

    if constants.ENABLE_SENTRY_CRASH_REPORTING:
        addon_dir = os.path.dirname(os.path.realpath(__file__))
        external_dir = os.path.join(addon_dir, 'external')
        sys.path.append(external_dir)
        import sentry_sdk
        from . import version

        api_key = aqt.mw.addonManager.getConfig(__name__).get('api_key', None)

        # setup crash reporting
        # =====================

        def sentry_filter(event, hint):
            if 'exc_info' in hint:
                exc_type, exc_value, tb = hint['exc_info']

                event['contexts']['cloudlanguagetools'] = {'user_id': api_key}

                # do we recognize the paths in this stack trace ?
                relevant_exception = False
                stack_summary = traceback.extract_tb(tb)
                for stack_frame in stack_summary:
                    filename = stack_frame.filename
                    if 'anki-hyper-tts' in filename or '771677663' in filename:
                        relevant_exception = True
                
                # if not, discard
                if not relevant_exception:
                    return None

            return event

        # need to create an anki-hyper-tts project in sentry.io first
        sentry_sdk.init(
            "https://a4170596966d47bb9f8fda74a9370bc7@o968582.ingest.sentry.io/6170140",
            traces_sample_rate=1.0,
            release=f'anki-hyper-tts@{version.ANKI_HYPER_TTS_VERSION}-{anki.version}',
            environment=os.environ.get('SENTRY_ENV', 'production'),
            before_send=sentry_filter
        )

    # initialize hypertts
    # ===================

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y%m%d-%H:%M:%S',
                        stream=sys.stdout,
                        level=logging.DEBUG)    

    ankiutils = anki_utils.AnkiUtils()

    def services_dir():
        current_script_path = os.path.realpath(__file__)
        current_script_dir = os.path.dirname(current_script_path)    
        return os.path.join(current_script_dir, 'services')
    service_manager = servicemanager.ServiceManager(services_dir(), 'services')
    service_manager.init_services()    
    hyper_tts = hypertts.HyperTTS(ankiutils, service_manager)
    # configure services based on config
    service_manager.configure(hyper_tts.get_configuration())
    gui.init(hyper_tts)
