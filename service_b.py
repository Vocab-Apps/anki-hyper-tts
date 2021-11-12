import service

class ServiceB(service.ServiceBase):
    def __init__(self):
        pass

    def voice_list(self):
        return ['voice B 1', 'voice B 2']