import sys
import logging

def pytest_configure(config):
    sys._pytest_mode = True
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', 
                        datefmt='%Y%m%d-%H:%M:%S',
                        level=logging.DEBUG)    

def pytest_unconfigure(config):
    del sys._pytest_mode