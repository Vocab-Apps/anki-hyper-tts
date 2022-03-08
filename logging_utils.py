import sys
import logging

constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)

def get_child_logger(name):
    root_logger = logging.getLogger(constants.LOGGER_NAME)
    return root_logger.getChild(name)