import sys
import os
import importlib
import logging
import typing
import requests


if hasattr(sys, '_pytest_mode'):
    import voice
    import service
    import errors
else:
    # import running from within Anki
    from . import voice
    from . import service
    from . import errors


class ServiceManager():
    """
    this class will discover the services that are available and query their voices. it can also route a request
    to the correct service.
    """
    def __init__(self, services_directory, package_name):
        self.services_directory = services_directory
        self.package_name = package_name
        self.services = {}
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

    # only used in testing
    def unload_services(self):
        module_names = self.discover_services()
        logging.info(sys.modules.keys())
        for module_name in module_names:
            full_name = f'{self.package_name}.{module_name}'
            logging.info(f'unloading module {full_name}')
            del sys.modules[full_name]

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

    def configure_cloudlanguagetools(self, api_key):
        logging.info('configure_cloudlanguagetools')
        self.cloudlanguagetools_base_url = os.environ.get('ANKI_LANGUAGE_TOOLS_BASE_URL', 'https://cloud-language-tools-tts-prod.anki.study')
        self.cloudlanguagetools_api_key = api_key
        self.cloudlanguagetools_enabled = True
        # enable all services which are supported by cloud language tools
        for service in self.get_all_services():
            if service.cloudlanguagetools_enabled():
                logging.info(f'enabling {service.name} with cloud language tools')
                service.set_enabled(True)

    def service_configuration_options(self, service_name):
        return self.services[service_name].configuration_options()

    # getting TTS audio and voice list
    # ================================

    def get_tts_audio(self, source_text, voice, options):
        if self.cloudlanguagetools_enabled:
            return self.get_tts_audio_cloudlanguagetools(source_text, voice, options)
        else:
            return voice.service.get_tts_audio(source_text, voice, options)

    def get_tts_audio_cloudlanguagetools(self, source_text, voice, options):
        # query cloud language tools API
        url_path = '/audio_v2'
        full_url = self.cloudlanguagetools_base_url + url_path
        data = {
            'text': source_text,
            'service': voice.service.name,
            'request_mode': 'batch',
            'language_code': voice.language.lang.name,
            'voice_key': voice.voice_key,
            'options': options
        }
        logging.info(f'request url: {full_url}, data: {data}')
        response = requests.post(full_url, json=data, headers={'api_key': self.cloudlanguagetools_api_key, 'client': 'languagetools', 'client_version': 'v0.01'})

        if response.status_code == 200:
            return response.content
        else:
            error_message = f"Status code: {response.status_code} ({response.content})"
            logging.error(error_message)
            raise errors.RequestError(source_text, voice, error_message)

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