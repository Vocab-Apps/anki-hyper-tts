from re import sub
import sys
import os
import importlib
import typing
import requests


voice = __import__('voice', globals(), locals(), [], sys._addon_import_level_base)
service = __import__('service', globals(), locals(), [], sys._addon_import_level_base)
errors = __import__('errors', globals(), locals(), [], sys._addon_import_level_base)
version = __import__('version', globals(), locals(), [], sys._addon_import_level_base)
constants = __import__('constants', globals(), locals(), [], sys._addon_import_level_base)
config_models = __import__('config_models', globals(), locals(), [], sys._addon_import_level_base)
cloudlanguagetools_module = __import__('cloudlanguagetools', globals(), locals(), [], sys._addon_import_level_base)
logging_utils = __import__('logging_utils', globals(), locals(), [], sys._addon_import_level_base)
logger = logging_utils.get_child_logger(__name__)

if hasattr(sys, '_sentry_crash_reporting'):
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
        hypertts_pro_mode = configuration_model.hypertts_pro_api_key_set()
        for service_name, enabled in configuration_model.get_service_enabled_map().items():
            if not self.service_exists(service_name):
                logger.error(f'could not find service {service_name}, cannot configure')
                continue
            service = self.get_service(service_name)
            logger.info(f'configuring service {service_name}, hypertts_pro_mode: {hypertts_pro_mode}, clt_enabled: {service.cloudlanguagetools_enabled()}')
            if not (hypertts_pro_mode == True and service.cloudlanguagetools_enabled()):
                service.enabled = enabled
                # do we need to set configuration for this service ? only do so if the service is enabled
                if enabled and service_name in configuration_model.get_service_config():
                    service_config = configuration_model.get_service_config()[service_name]
                    service.configure(service_config)
        # if we enable cloudlanguagetools, it may force some services to enabled
        self.cloudlanguagetools.configure(configuration_model)
        if hypertts_pro_mode:
            self.configure_cloudlanguagetools(configuration_model)
        else:
            self.cloudlanguagetools_enabled = False

    def remove_non_existent_services(self, configuration_model):
        # remove non existent services from the service enabled map
        service_enabled_map = configuration_model.get_service_enabled_map()
        service_list = list(service_enabled_map.keys())
        for service_name in service_list:
            if not self.service_exists(service_name):
                del service_enabled_map[service_name]
        # do the same thing from the service config map
        service_config_map = configuration_model.get_service_config()
        service_list = list(service_config_map.keys())
        for service_name in service_list:
            if not self.service_exists(service_name):
                del service_config_map[service_name]        
        configuration_model.set_service_enabled_map(service_enabled_map)
        configuration_model.set_service_config(service_config_map)

        return configuration_model

            

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
        logger.info(f'discovered {len(module_names)} services')
        # sys.path.insert(0, self.services_directory)
        for module_name in module_names:
            logger.info(f'importing module {module_name}')
            __import__(self.package_name, globals(), locals(), [module_name], sys._addon_import_level_base)

    def instantiate_services(self):
        for subclass in service.ServiceBase.__subclasses__():
            subclass_instance = subclass()
            if subclass_instance.test_service() and self.allow_test_services == False:
                logger.info(f'skipping test service {subclass_instance.name}')
                continue
            logger.info(f'instantiating service {subclass_instance.name}')
            self.services[subclass_instance.name] = subclass_instance

    def service_exists(self, service_name):
        return service_name in self.services
    
    def get_service(self, service_name):
        return self.services[service_name]

    def get_all_services(self):
        return list(self.services.values())

    # service configuration
    # =====================

    def configure_cloudlanguagetools(self, configuration: config_models.Configuration):
        logger.info('configure_cloudlanguagetools')
        self.cloudlanguagetools_enabled = True
        # enable all services which are supported by cloud language tools
        for service in self.get_all_services():
            if service.cloudlanguagetools_enabled():
                logger.info(f'enabling {service.name} with cloud language tools')
                service.enabled = True

    def service_configuration_options(self, service_name):
        return self.services[service_name].configuration_options()

    # getting TTS audio and voice list
    # ================================

    def use_cloud_language_tools(self, voice):
        if self.cloudlanguagetools_enabled:
            if voice.service.cloudlanguagetools_enabled():
                return True
        return False

    def get_tts_audio(self, source_text, voice, options, audio_request_context):
        if hasattr(sys, '_sentry_crash_reporting'):
            return self.get_tts_audio_instrumented(source_text, voice, options, audio_request_context)
        else:
            return self.get_tts_audio_implementation(source_text, voice, options, audio_request_context)

    def get_tts_audio_instrumented(self, source_text, voice, options, audio_request_context):
        transaction_name = f'{voice.service.name}'
        if self.use_cloud_language_tools(voice):
            transaction_name = f'cloudlanguagetools_{voice.service.name}'
        sentry_sdk.set_tag('clt.audio_request_reason', audio_request_context.get_audio_request_reason_tag())
        raise_exception = None
        with sentry_sdk.start_transaction(op="audio", name=transaction_name) as transaction:
            try:
                result_audio = self.get_tts_audio_implementation(source_text, voice, options, audio_request_context)
                transaction.status = 'ok'
                return result_audio
            except Exception as e:
                transaction.status = 'invalid_argument'
                sentry_sdk.set_context("audio_request", {
                    'text': source_text,
                    'voice': str(voice),
                    'error': str(e)
                })
                raise_exception = e
        if raise_exception != None:
            raise raise_exception

    def get_tts_audio_implementation(self, source_text, voice, options, audio_request_context):
        if self.use_cloud_language_tools(voice):
            return self.cloudlanguagetools.get_tts_audio(source_text, voice, options, audio_request_context)
        else:
            return voice.service.get_tts_audio(source_text, voice, options)

    def full_voice_list(self, single_service_name=None) -> typing.List[voice.VoiceBase]:
        full_list = []
        for service_name, service_instance in self.services.items():
            if single_service_name != None:
                # we only want voices for a particular service
                if service_name != single_service_name:
                    continue
            logger.debug(f'getting voice list for service {service_name}, enabled: {service_instance.enabled}')
            if service_instance.enabled:
                voices = service_instance.voice_list()
                logger.debug(f'got {len(voices)} voices from service {service_name}')
                full_list.extend(voices)
        return full_list

    def deserialize_voice(self, voice_data):
        # avoid loading voice list for services we don't need, this is particularly important for ElevenLabsCustom which does
        # an actual query to their API
        voice_list = self.full_voice_list(single_service_name=voice_data['service'])
        voice_subset = [voice for voice in voice_list if voice.voice_key == voice_data['voice_key'] and voice.service.name == voice_data['service']]
        if len(voice_subset) == 0:
            raise errors.VoiceNotFound(voice_data)
        return voice_subset[0]