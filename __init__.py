import sys
import os

# add external modules to sys.path, for 3rd party modules
addon_dir = os.path.dirname(os.path.realpath(__file__))
external_dir = os.path.join(addon_dir, 'external')
sys.path.insert(0, external_dir)

# import hypertts which should do the anki setup
from . import hypertts