import sys
import logging

constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)

def get_stream_handler():
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', datefmt='%H:%M:%S'))
    return handler

def get_file_handler(filename):
    handler = logging.FileHandler(filename)
    handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', datefmt='%H:%M:%S'))
    return handler    

def configure_console_logging():
    root_logger = logging.getLogger(constants.LOGGER_NAME)
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(get_stream_handler())

def configure_file_logging(filename):
    root_logger = logging.getLogger(constants.LOGGER_NAME)
    root_logger.setLevel(logging.DEBUG)    
    root_logger.addHandler(get_file_handler(filename))

def configure_silent():
    root_logger = logging.getLogger(constants.LOGGER_NAME)
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(logging.NullHandler())

def get_child_logger(name):
    root_logger = logging.getLogger(constants.LOGGER_NAME)
    return root_logger.getChild(name)

def get_test_child_logger(name):
    root_logger = logging.getLogger(constants.LOGGER_NAME_TEST)
    return root_logger.getChild(name)