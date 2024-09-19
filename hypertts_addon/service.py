import sys
import abc
import json
import os
import functools
import databind.json
from posixpath import dirname
import typing

from . import constants
from . import voice as voice_module
from . import languages
from . import errors
from . import logging_utils

from .services import voicelist

logger = logging_utils.get_child_logger(__name__)


class ServiceBase(abc.ABC):
    def __init__(self):
        self._config = {}
    
    """service name"""
    def _get_name(self):
        return type(self).__name__

    name = property(fget=_get_name)

    # enable/disable the service
    def _get_enabled(self):
        if not hasattr(self, '_enabled'):
            return self.enabled_by_default()
        if self._enabled == None:
            return False
        return self._enabled
    
    def _set_enabled(self, enabled):
        self._enabled = enabled

    enabled = property(fget=_get_enabled, fset=_set_enabled)

    # whether the service is supported by cloud-language-tools
    def cloudlanguagetools_enabled(self):
        return False # default

    # whether the service is enabled by default
    def enabled_by_default(self):
        return False

    @property
    @abc.abstractmethod
    def service_type(self) -> constants.ServiceType:
        pass

    @property
    @abc.abstractmethod
    def service_fee(self) -> constants.ServiceFee:
        pass    

    def test_service(self):
        return False

    @abc.abstractmethod
    def voice_list(self) -> typing.List[voice_module.TtsVoice_v3]:
        pass

    @abc.abstractmethod
    def get_tts_audio(self, source_text, voice: voice_module.TtsVoice_v3, options):
        pass


    # some helper functions
    def basic_voice_list(self) -> typing.List[voice_module.TtsVoice_v3]:
        """basic processing for voice list which should work for most services which are represented in voicelist.py"""
        voice_list = voicelist.VOICE_LIST
        service_voices = [voice_candidate for voice_candidate in voice_list if voice_candidate.service == self.name]
        return service_voices

    # the following functions can be overriden if a service requires configuration
    def configuration_options(self):
        return {}

    def configure(self, config):
        self._config = config

    def get_configuration_value_mandatory(self, key):
        value = self._config.get(key, None)
        if value == None or (self.configuration_options()[key] == str and len(value) == 0):
            raise errors.MissingServiceConfiguration(self.name, key)
        return value

    def get_configuration_value_optional(self, key, default_value):
        return self._config.get(key, default_value)

