import os
import importlib
import logging
import typing
import voice
import service
import errors

class ServiceManager():
    """
    this class will discover the services that are available and query their voices. it can also route a request
    to the correct service.
    """
    def __init__(self, services_directory, package_name=None):
        self.services_directory = services_directory
        self.package_name = package_name
        self.services = {}

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
        for module_name in module_names:
            module_name = f'{self.package_name}.{module_name}'
            logging.info(f'importing module {module_name}')
            importlib.import_module(module_name)

    def instantiate_services(self):
        for subclass in service.ServiceBase.__subclasses__():
            subclass_instance = subclass()
            logging.info(f'instantiating service {subclass_instance.name}')
            self.services[subclass_instance.name] = subclass_instance

    def get_service(self, service_name):
        return self.services[service_name]

    def get_all_services(self):
        return self.services.values()

    # service configuration
    # =====================

    def service_configuration_options(self, service_name):
        return self.services[service_name].configuration_options()

    # getting TTS audio and voice list
    # ================================

    def get_tts_audio(self, source_text, voice):
        return voice.service.get_tts_audio(source_text, voice)

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