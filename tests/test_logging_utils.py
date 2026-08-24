import io
import logging
import sys

import pytest

from hypertts_addon import constants
from hypertts_addon import logging_utils


@pytest.fixture(autouse=True)
def restore_logging():
    """conftest.py configures console logging once for the whole session, and every test in this
    file reconfigures the same global logger. put the original handlers back when we're done, and
    dispose of the ones we created: a TextIOWrapper closes the stream it wraps when it is
    collected, which would take pytest's captured stdout down with it."""
    root_logger = logging_utils.get_root_logger()
    saved_handlers = list(root_logger.handlers)
    saved_propagate = root_logger.propagate
    saved_level = root_logger.level
    saved_remote_logging = logging_utils._remote_logging_enabled

    yield

    for handler in list(root_logger.handlers):
        if handler in saved_handlers:
            continue
        root_logger.removeHandler(handler)
        try:
            if isinstance(handler, logging.FileHandler):
                handler.close()
            elif isinstance(getattr(handler, 'stream', None), io.TextIOWrapper):
                handler.stream.detach()
        except ValueError:
            # the stream was already closed by whoever owns it
            pass

    root_logger.handlers = saved_handlers
    root_logger.propagate = saved_propagate
    root_logger.setLevel(saved_level)
    logging_utils._remote_logging_enabled = saved_remote_logging


def test_addon_logging_is_silent(monkeypatch, capsys):
    # pytest tests/test_logging_utils.py -k test_addon_logging_is_silent
    monkeypatch.delenv(logging_utils.ENV_DEBUG_LOGGING, raising=False)
    monkeypatch.delenv(logging_utils.ENV_DEBUG_LOGFILE, raising=False)

    logging_utils.configure_addon_logging()

    root_logger = logging_utils.get_root_logger()
    # a NullHandler and nothing else: it keeps logging.lastResort from writing to stderr, which
    # anki would turn into a confusing error message for the user
    assert len(root_logger.handlers) == 1
    assert isinstance(root_logger.handlers[0], logging.NullHandler)
    assert root_logger.propagate == False
    assert root_logger.level == logging.DEBUG

    logger = logging_utils.get_child_logger('hypertts_addon.test_module')
    logger.debug('debug message')
    logger.info('info message')
    logger.warning('warning message')
    logger.error('error message')
    logger.critical('critical message')
    try:
        raise ValueError('test exception')
    except ValueError:
        logger.exception('exception message')

    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err == ''


def test_addon_file_logging(monkeypatch, capsys, tmp_path):
    # pytest tests/test_logging_utils.py -k test_addon_file_logging
    logfile = tmp_path / 'hypertts.log'
    monkeypatch.setenv(logging_utils.ENV_DEBUG_LOGGING, 'file')
    monkeypatch.setenv(logging_utils.ENV_DEBUG_LOGFILE, str(logfile))

    logging_utils.configure_addon_logging()

    logger = logging_utils.get_child_logger('hypertts_addon.test_module')
    logger.info('info message with unicode 日本語')
    logger.debug('debug message')

    for handler in logging_utils.get_root_logger().handlers:
        handler.flush()

    contents = logfile.read_text(encoding='utf-8')
    assert 'info message with unicode 日本語' in contents
    assert 'debug message' in contents
    # still nothing on stdout/stderr
    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err == ''


def test_addon_file_logging_without_filename(monkeypatch):
    """HYPER_TTS_DEBUG_LOGGING=file without HYPER_TTS_DEBUG_LOGFILE must not blow up addon startup"""
    # pytest tests/test_logging_utils.py -k test_addon_file_logging_without_filename
    monkeypatch.setenv(logging_utils.ENV_DEBUG_LOGGING, 'file')
    monkeypatch.delenv(logging_utils.ENV_DEBUG_LOGFILE, raising=False)

    logging_utils.configure_addon_logging()

    root_logger = logging_utils.get_root_logger()
    assert len(root_logger.handlers) == 1
    assert isinstance(root_logger.handlers[0], logging.NullHandler)


class FakeStdout:
    """stands in for sys.stdout: _console_handler() wraps sys.stdout.buffer, and handing it
    pytest's captured stdout means the wrapper and the capture fixture fight over who closes it"""
    def __init__(self):
        self.buffer = io.BytesIO()
        self.encoding = 'utf-8'


def test_console_logging(monkeypatch):
    # pytest tests/test_logging_utils.py -k test_console_logging
    fake_stdout = FakeStdout()
    monkeypatch.setattr(sys, 'stdout', fake_stdout)
    monkeypatch.setenv(logging_utils.ENV_DEBUG_LOGGING, 'enable')
    logging_utils.configure_addon_logging()

    logger = logging_utils.get_child_logger('hypertts_addon.test_module')
    logger.info('console message with unicode 日本語')

    for handler in logging_utils.get_root_logger().handlers:
        handler.flush()

    output = fake_stdout.buffer.getvalue().decode('utf-8')
    assert 'console message with unicode 日本語' in output
    # the formatter carries the call site, which is what makes the debug logs readable
    assert 'INFO' in output
    assert 'hypertts.test_module' in output


def test_get_child_logger():
    # pytest tests/test_logging_utils.py -k test_get_child_logger
    logger = logging_utils.get_child_logger('hypertts_addon.services.service_azure')
    assert isinstance(logger, logging.Logger)
    assert logger.name == f'{constants.LOGGER_NAME}.service_azure'
    # the whole stdlib api, which the hand rolled loggers this replaced didn't have
    assert hasattr(logger, 'exception')
    assert hasattr(logger, 'log')


def test_get_test_child_logger():
    # pytest tests/test_logging_utils.py -k test_get_test_child_logger
    logger = logging_utils.get_test_child_logger('tests.test_logging_utils')
    assert logger.name == f'{constants.LOGGER_NAME_TEST}.tests.test_logging_utils'


def test_enable_sentry_remote_logging_without_crash_reporting(monkeypatch):
    """without crash reporting there is no sentry client, remote logging must stay off"""
    # pytest tests/test_logging_utils.py -k test_enable_sentry_remote_logging_without_crash_reporting
    monkeypatch.delattr(sys, '_sentry_crash_reporting', raising=False)
    monkeypatch.setattr(logging_utils, '_remote_logging_enabled', False)
    logging_utils.configure_addon_logging()

    logging_utils.enable_sentry_remote_logging()

    assert logging_utils._remote_logging_enabled == False
    assert len(logging_utils.get_root_logger().handlers) == 1


def test_enable_sentry_remote_logging_is_idempotent(monkeypatch):
    """the feature flag can turn this on long after startup, and after the preference already did"""
    # pytest tests/test_logging_utils.py -k test_enable_sentry_remote_logging_is_idempotent
    from sentry_sdk.integrations.logging import LoggingIntegration, SentryLogsHandler

    monkeypatch.setattr(sys, '_sentry_crash_reporting', True, raising=False)
    monkeypatch.setattr(logging_utils, '_remote_logging_enabled', False)
    monkeypatch.setattr(LoggingIntegration, 'capture_sentry_logs', False)
    logging_utils.configure_addon_logging()

    logging_utils.enable_sentry_remote_logging()
    logging_utils.enable_sentry_remote_logging()

    root_logger = logging_utils.get_root_logger()
    sentry_handlers = [handler for handler in root_logger.handlers
        if isinstance(handler, SentryLogsHandler)]
    assert len(sentry_handlers) == 1
    assert LoggingIntegration.capture_sentry_logs == True


def test_disable_sentry_remote_logging(monkeypatch):
    """turning the preference back off must stop shipping logs right away, without a restart"""
    # pytest tests/test_logging_utils.py -k test_disable_sentry_remote_logging
    from sentry_sdk.integrations.logging import LoggingIntegration, SentryLogsHandler

    monkeypatch.setattr(sys, '_sentry_crash_reporting', True, raising=False)
    monkeypatch.setattr(logging_utils, '_remote_logging_enabled', False)
    monkeypatch.setattr(LoggingIntegration, 'capture_sentry_logs', False)
    logging_utils.configure_addon_logging()

    logging_utils.enable_sentry_remote_logging()
    logging_utils.disable_sentry_remote_logging()

    root_logger = logging_utils.get_root_logger()
    assert [handler for handler in root_logger.handlers
        if isinstance(handler, SentryLogsHandler)] == []
    assert logging_utils._remote_logging_enabled == False

    # off again is a no-op, and it can be turned back on
    logging_utils.disable_sentry_remote_logging()
    logging_utils.enable_sentry_remote_logging()
    assert len([handler for handler in root_logger.handlers
        if isinstance(handler, SentryLogsHandler)]) == 1
    assert logging_utils._remote_logging_enabled == True
