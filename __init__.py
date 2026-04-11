import sys
import os

if (
    'pytest' in sys.modules
    or os.environ.get('PYTEST_CURRENT_TEST') is not None
    or any('pytest' in arg for arg in sys.argv)
):
    sys._pytest_mode = True

# add external modules to sys.path, for 3rd party modules
addon_dir = os.path.dirname(os.path.realpath(__file__))
external_dir = os.path.join(addon_dir, 'external')
sys.path.insert(0, external_dir)

# Add the current directory to sys.path
sys.path.insert(0, addon_dir)

# import hypertts which should do the anki setup
if not hasattr(sys, '_pytest_mode'):
    import hypertts_addon
