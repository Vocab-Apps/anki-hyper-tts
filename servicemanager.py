from re import sub
import sys
import os
import importlib
import logging
import typing
import requests

voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_base)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
version = __import__('version', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
cloudlanguagetools_module = __import__('cloudlanguagetools', globals(), locals(), [], sys._addon_import_level_base)

if constants.ENABLE_SENTRY_CRASH_REPORTING:
    import sentry_sdk

class ServiceManager():
    """
    this class will discover the services that are available and query their voices. it can also route a request
    to the correct service.
    """
    def __init__(self, services_directory, package_name, allow_test_services, cloudlanguagetools=cloudlanguagetools_module.CloudLanguageTools()):
        self.services_directory = services_directory
        self.package_name = package_name
        self.services = {}
        self.cloudlanguagetools_enabled = False
        self.allow_test_services = allow_test_services
        self.cloudlanguagetools = cloudlanguagetools

    def configure(self, configuration_model):
        for service_name, enabled in configuration_model.get_service_enabled_map().items():
            service = self.get_service(service_name)
            service.enabled = enabled
        for service_name, config in configuration_model.get_service_config().items():
            service = self.get_service(service_name)
            service.configure(config)
        # if we enable cloudlanguagetools, it may force some services to enabled
        if configuration_model.hypertts_pro_api_key_set():
            self.configure_cloudlanguagetools(configuration_model.hypertts_pro_api_key)
        else:
            self.cloudlanguagetools_enabled = False

    # service discovery
    # =================

    def discover_services(self):
        module_names = []
        for path, dirs, files in os.walk(self.services_directory):
            for filename in files:
                if filename.startswith('service_') and filename.endswith('.py'):
                    module_name = filename.replace('.py', '')        
                    module_names.append(module_name)
        return module_names

    def init_services(self):
        self.import_services()
        self.instantiate_services()

    def import_services(self):
        module_names = self.discover_services()
        logging.info(f'discovered {len(module_names)} services')
        # sys.path.insert(0, self.services_directory)
        for module_name in module_names:
            logging.info(f'importing module {module_name}')
            __import__(self.package_name, globals(), locals(), [module_name], sys._addon_import_level_base)

    def instantiate_services(self):
        for subclass in service.ServiceBase.__subclasses__():
            subclass_instance = subclass()
            if subclass_instance.test_service() and self.allow_test_services == False:
                logging.info(f'skipping test service {subclass_instance.name}')
                continue
            logging.info(f'instantiating service {subclass_instance.name}')
            self.services[subclass_instance.name] = subclass_instance

    def get_service(self, service_name):
        return self.services[service_name]

    def get_all_services(self):
        return self.services.values()

    # service configuration
    # =====================

    def configure_cloudlanguagetools(self, api_key):
        logging.info('configure_cloudlanguagetools')
        self.cloudlanguagetools.configure(api_key)
        self.cloudlanguagetools_enabled = True
        # enable all services which are supported by cloud language tools
        for service in self.get_all_services():
            if service.cloudlanguagetools_enabled():
                logging.info(f'enabling {service.name} with cloud language tools')
                service.enabled = True

    def service_configuration_options(self, service_name):
        return self.services[service_name].configuration_options()

    # getting TTS audio and voice list
    # ================================

    def get_tts_audio(self, source_text, voice, options):
        with sentry_sdk.start_transaction(op="get_tts_audio", name='test_transaction') as transaction:
            if self.cloudlanguagetools_enabled:
                return self.cloudlanguagetools.get_tts_audio(source_text, voice, options)
            else:
                return voice.service.get_tts_audio(source_text, voice, options)

    def full_voice_list(self) -> typing.List[voice.VoiceBase]:
        full_list = []
        for service_name, service_instance in self.services.items():
            if service_instance.enabled:
                voices = service_instance.voice_list()
                full_list.extend(voices)
        return full_list

    def deserialize_voice(self, voice_data):
        voice_list = self.full_voice_list()
        voice_subset = [voice for voice in voice_list if voice.voice_key == voice_data['voice_key'] and voice.service.name == voice_data['service']]
        if len(voice_subset) == 0:
            raise errors.VoiceNotFound(voice_data)
        return voice_subset[0]