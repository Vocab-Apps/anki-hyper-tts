import sys
import logging

def pytest_configure(config):
    sys._pytest_mode = True
    sys._addon_import_level_base = 0
    sys._addon_import_level_services = 0
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', 
                        datefmt='%Y%m%d-%H:%M:%S',
                        level=logging.DEBUG)    

def pytest_unconfigure(config):
    del sys._pytest_mode