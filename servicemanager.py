import os
import importlib
import logging
import typing
import voice
import service

class ServiceManager():
    """
    this class will discover the services that are available and query their voices. it can also route a request
    to the correct service.
    """
    def __init__(self, services_directory, package_name=None):
        self.services_directory = services_directory
        self.package_name = package_name

    def discover_services(self):
        module_names = []
        for path, dirs, files in os.walk(self.services_directory):
            for filename in files:
                if filename.startswith('service_') and filename.endswith('.py'):
                    module_name = filename.replace('.py', '')        
                    module_names.append(module_name)
        return module_names

    def import_services(self):
        module_names = self.discover_services()
        for module_name in module_names:
            module_name = f'{self.package_name}.{module_name}'
            logging.info(f'importing module {module_name}')
            importlib.import_module(module_name)

    def get_tts_audio(self, source_text, voice):
        # to be implemented
        return None

    def full_voice_list(self) -> typing.List[voice.VoiceBase]:
        full_list = []
        for subclass in service.ServiceBase.__subclasses__():
            subclass_instance = subclass()
            voices = subclass_instance.voice_list()
            full_list.extend(voices)
        return full_list
