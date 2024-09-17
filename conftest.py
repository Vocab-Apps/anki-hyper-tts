import sys
import os
import anki.lang

def pytest_configure(config):
    sys._pytest_mode = True

    # configure sys.path
    root_dir = os.path.dirname(os.path.realpath(__file__))
    external_dir = os.path.join(root_dir, 'external')

    sys.path.insert(0, external_dir)
    sys.path.insert(0, root_dir)

    from hypertts import logging_utils
    logging_utils.configure_console_logging()
    # required to access some anki functions such as anki.utils.html_to_text_line
    anki.lang.set_lang('en_US')

def pytest_unconfigure(config):
    del sys._pytest_mode