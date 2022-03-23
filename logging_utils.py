import sys
import logging

if hasattr(sys, '_sentry_crash_reporting'):
    import sentry_sdk

constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)

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
class BreadcrumbLogger():
    def __init__(self, name):
        self.name = name
    
    def send_breadcrumb(self, level, msg):
        sentry_sdk.add_breadcrumb(
            type='log',
            message=msg,
            level=level,
        )        

    def debug(self, msg, *args, **kwargs):
        self.send_breadcrumb('debug', msg)

    def info(self, msg, *args, **kwargs):
        self.send_breadcrumb('info', msg)

    def warning(self, msg, *args, **kwargs):
        self.send_breadcrumb('warning', msg)

    def error(self, msg, *args, **kwargs):
        self.send_breadcrumb('error', msg)

    def critical(self, msg, *args, **kwargs):
        self.send_breadcrumb('fatal', msg)

def get_stream_handler():
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', datefmt='%H:%M:%S'))
    return handler

def get_file_handler(filename):
    handler = logging.FileHandler(filename)
    handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', datefmt='%H:%M:%S'))
    return handler    

def configure_console_logging():
    global SILENT_LOGGING_MODE
    SILENT_LOGGING_MODE = False
    root_logger = logging.getLogger(constants.LOGGER_NAME)
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(get_stream_handler())

def configure_file_logging(filename):
    global SILENT_LOGGING_MODE
    SILENT_LOGGING_MODE = False
    root_logger = logging.getLogger(constants.LOGGER_NAME)
    root_logger.setLevel(logging.DEBUG)    
    root_logger.addHandler(get_file_handler(filename))

def configure_silent():
    SILENT_LOGGING_MODE = True

def get_child_logger(name):
    if SILENT_LOGGING_MODE:
        if hasattr(sys, '_sentry_crash_reporting'):
            return BreadcrumbLogger(name)
        else:
            return NullLogger()
    else:
        root_logger = logging.getLogger(constants.LOGGER_NAME)
        return root_logger.getChild(name)


def get_test_child_logger(name):
    root_logger = logging.getLogger(constants.LOGGER_NAME_TEST)
    return root_logger.getChild(name)