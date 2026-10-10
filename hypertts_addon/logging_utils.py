import sys
import os
import io
import logging

from . import constants

LOG_FORMAT = '%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(name)s: %(message)s'
DATE_FORMAT = '%H:%M:%S'

ENV_DEBUG_LOGGING = 'HYPER_TTS_DEBUG_LOGGING'
ENV_DEBUG_LOGFILE = 'HYPER_TTS_DEBUG_LOGFILE'

_remote_logging_enabled = False


def get_root_logger():
    return logging.getLogger(constants.LOGGER_NAME)

def _get_formatter():
    return logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

def _console_handler():
    # Wrap stdout to handle encoding errors gracefully on Windows (cp1252)
    # This prevents UnicodeEncodeError when logging non-ASCII characters
    wrapped_stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding=sys.stdout.encoding,
        errors='backslashreplace',
        line_buffering=True
    )
    handler = logging.StreamHandler(stream=wrapped_stdout)
    handler.setFormatter(_get_formatter())
    return handler

def _file_handler(filename):
    # Use UTF-8 encoding to properly handle all Unicode characters
    handler = logging.FileHandler(filename, encoding='utf-8')
    handler.setFormatter(_get_formatter())
    return handler

def _reset_root_logger():
    """the hypertts logger never propagates to anki's root logger, and always carries a
    NullHandler so that logging.lastResort (stderr, WARNING and above) can never fire: anki turns
    anything written to stderr into a confusing error message for the user"""
    root_logger = get_root_logger()
    root_logger.handlers.clear()
    root_logger.propagate = False
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(logging.NullHandler())
    return root_logger

def configure_addon_logging():
    """running inside anki: nothing is written to stdout or stderr unless the user asks for it with
    HYPER_TTS_DEBUG_LOGGING. sentry still sees every record, its LoggingIntegration hooks
    logging.Logger.callHandlers rather than installing a handler."""
    root_logger = _reset_root_logger()
    debug_logging = os.environ.get(ENV_DEBUG_LOGGING, '')
    if debug_logging == 'enable':
        root_logger.addHandler(_console_handler())
    elif debug_logging == 'file':
        logfile = os.environ.get(ENV_DEBUG_LOGFILE, '')
        if logfile:
            root_logger.addHandler(_file_handler(logfile))

def configure_console_logging():
    """used by the test suite and command line tools, which are free to write to stdout"""
    root_logger = _reset_root_logger()
    root_logger.addHandler(_console_handler())

def enable_sentry_remote_logging():
    """ship hypertts log records to sentry logs. this is the single switch for the feature: it's
    called from the startup preference, and from the sentry-full-reporting feature flag, which is
    only known well after sentry_sdk.init, so it has to be safe to call late and more than once."""
    global _remote_logging_enabled
    if _remote_logging_enabled or not hasattr(sys, '_sentry_crash_reporting'):
        return
    from sentry_sdk.integrations.logging import LoggingIntegration, SentryLogsHandler
    # class level switch which gates SentryLogsHandler.emit. sentry_sdk.init normally sets it from
    # the LoggingIntegration constructor, but the feature flag can turn this on afterwards
    LoggingIntegration.capture_sentry_logs = True
    # our own logger only, so that we don't upload anki's logging or that of other addons
    get_root_logger().addHandler(SentryLogsHandler(level=logging.DEBUG))
    _remote_logging_enabled = True

def disable_sentry_remote_logging():
    """stop shipping hypertts log records to sentry logs. the counterpart of
    enable_sentry_remote_logging(), so that turning the preference off takes effect right away
    instead of at the next anki restart."""
    global _remote_logging_enabled
    if not _remote_logging_enabled:
        return
    from sentry_sdk.integrations.logging import SentryLogsHandler
    root_logger = get_root_logger()
    for handler in list(root_logger.handlers):
        if isinstance(handler, SentryLogsHandler):
            root_logger.removeHandler(handler)
    _remote_logging_enabled = False

def get_child_logger(name):
    child_logger_name = name.split('.')[-1]
    return get_root_logger().getChild(child_logger_name)

def get_test_child_logger(name):
    root_logger = logging.getLogger(constants.LOGGER_NAME_TEST)
    return root_logger.getChild(name)
