import sys
import os
import traceback
import anki
import aqt

if hasattr(sys, '_pytest_mode'):
    # called from within a test run
    pass
else:
    # setup sentry crash reporting
    # ============================

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
                if 'anki-language-tools' in filename or '771677663' in filename:
                    relevant_exception = True
            
            # if not, discard
            if not relevant_exception:
                return None

        return event

    sentry_sdk.init(
        "https://dbee54f0eff84f0db037e995ae46df11@o968582.ingest.sentry.io/5920286",
        traces_sample_rate=1.0,
        release=f'anki-language-tools@{version.ANKI_LANGUAGE_TOOLS_VERSION}-{anki.version}',
        environment=os.environ.get('SENTRY_ENV', 'production'),
        before_send=sentry_filter
    )

    # initialize languagetools
    # ========================

    from . import languagetools
    from . import gui
    from . import editor
    from . import anki_utils
    from . import deck_utils
    from . import cloudlanguagetools
    from . import errors

    ankiutils = anki_utils.AnkiUtils()
    deckutils = deck_utils.DeckUtils(ankiutils)
    cloud_language_tools = cloudlanguagetools.CloudLanguageTools()
    languagetools = languagetools.LanguageTools(ankiutils, deckutils, cloud_language_tools)
    gui.init(languagetools)
    editor.init(languagetools)
