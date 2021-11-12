import service

class ServiceA(service.ServiceBase):
    def __init__(self):
        pass

    def voice_list(self):
        return ['voice A 1', 'voice A 2' ]