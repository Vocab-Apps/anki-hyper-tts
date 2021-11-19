import os

class ServiceManager():
    """
    this class will discover the services that are available and query their voices. it can also route a request
    to the correct service.
    """
    def __init__(self, services_directory):
        self.services_directory = services_directory

    def discover_services(self):
        module_names = []
        for path, dirs, files in os.walk(self.services_directory):
            for filename in files:
                if filename.startswith('service_') and filename.endswith('.py'):
                    module_name = filename.replace('.py', '')        
                    module_names.append(module_name)
        return module_names

    def get_tts_audio(self, source_text, voice):
        # to be implemented
        return None
