import sys
import os
import io
import logging
import inspect

if hasattr(sys, '_sentry_crash_reporting'):
    import sentry_sdk

from . import constants

SILENT_LOGGING_MODE = True

class NullLogger():
    def __init__(self):
        pass
    
    def debug(self, msg, *args, **kwargs):
        pass

    def info(self, msg, *args, **kwargs):
        pass    

    def warning(self, msg, *args, **kwargs):
        pass   

    def error(self, msg, *args, **kwargs):
        pass             

    def critical(self, msg, *args, **kwargs):
        pass

"""use this logger class to avoid any possibility of logging to stdout/stderr,
which may be caught by anki and will display a confusing error message to the user"""
class SentryLogger():
    def __init__(self, name):
        self.name = name
    
    def send_event(self, level, msg):
        if msg == None:
            return

        log_location = {}
        if level >= logging.ERROR:
            # extract data from stack
            caller = inspect.getframeinfo(inspect.stack()[2][0])
            pathname = caller.filename
            lineno = caller.lineno
            file = os.path.basename(pathname)
            log_location['line_number'] = lineno
            log_location['filename'] = file
        
        record = logging.LogRecord(self.name, level, '', 0, msg, None, None)
        if log_location != {}:
            record.__dict__['log_location'] = log_location
        integration = sentry_sdk.hub.Hub.current.get_integration(sentry_sdk.integrations.logging.LoggingIntegration)
        if integration != None:
            integration._handle_record(record)

    def debug(self, msg, *args, **kwargs):
        if msg == None:
            return
        self.send_event(logging.INFO, '[debug] ' + msg)

    def info(self, msg, *args, **kwargs):
        self.send_event(logging.INFO, msg)

    def warning(self, msg, *args, **kwargs):
        self.send_event(logging.WARNING, msg)

    def error(self, msg, *args, **kwargs):
        # check if exc_info=True was passed
        exc_info = kwargs.get('exc_info', None)
        if exc_info == True:
            sentry_sdk.capture_exception(msg)
        else:
            self.send_event(logging.ERROR, msg)

    def critical(self, msg, *args, **kwargs):
        self.send_event(logging.CRITICAL, msg)

def get_stream_handler():
    # Wrap stdout to handle encoding errors gracefully on Windows (cp1252)
    # This prevents UnicodeEncodeError when logging non-ASCII characters
    wrapped_stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding=sys.stdout.encoding,
        errors='backslashreplace',
        line_buffering=True
    )
    handler = logging.StreamHandler(stream=wrapped_stdout)
    handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(name)s: %(message)s', datefmt='%H:%M:%S'))
    return handler

def get_file_handler(filename):
    # Use UTF-8 encoding to properly handle all Unicode characters
    handler = logging.FileHandler(filename, encoding='utf-8')
    handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(name)s: %(message)s', datefmt='%H:%M:%S'))
    return handler    

def configure_console_logging():
    global SILENT_LOGGING_MODE
    SILENT_LOGGING_MODE = False
    root_logger = logging.getLogger(constants.LOGGER_NAME)
    root_logger.handlers.clear()
    root_logger.propagate = False
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(get_stream_handler())

def configure_file_logging(filename):
    global SILENT_LOGGING_MODE
    SILENT_LOGGING_MODE = False
    root_logger = logging.getLogger(constants.LOGGER_NAME)
    root_logger.handlers.clear()
    root_logger.propagate = False
    root_logger.setLevel(logging.DEBUG)    
    root_logger.addHandler(get_file_handler(filename))

def configure_silent():
    global SILENT_LOGGING_MODE
    SILENT_LOGGING_MODE = True

def get_child_logger(name):
    child_logger_name = name.split('.')[-1]
    if SILENT_LOGGING_MODE:
        if hasattr(sys, '_sentry_crash_reporting'):
            return SentryLogger(constants.LOGGER_NAME + '.' + child_logger_name)
        else:
            return NullLogger()
    else:
        root_logger = logging.getLogger(constants.LOGGER_NAME)
        return root_logger.getChild(child_logger_name)


def get_test_child_logger(name):
    root_logger = logging.getLogger(constants.LOGGER_NAME_TEST)
    return root_logger.getChild(name)