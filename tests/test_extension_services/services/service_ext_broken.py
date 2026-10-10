"""fixture third party service which fails at import time, the way a real extension would if it
depended on a python module which isn't bundled with HyperTTS or Anki. HyperTTS must start up
normally regardless."""

import this_module_does_not_exist_hypertts_test

from hypertts_addon import service


class ExtensionServiceBroken(service.ServiceBase):
    pass
