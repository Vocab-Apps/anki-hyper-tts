import sys

def pytest_configure(config):
    sys._pytest_mode = True
    sys._addon_import_level_base = 0
    sys._addon_import_level_services = 0
    import logging_utils
    logging_utils.configure_console_logging()

def pytest_unconfigure(config):
    del sys._pytest_mode