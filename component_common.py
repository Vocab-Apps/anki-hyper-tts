import abc

class ComponentBase(abc.ABC):
    @abc.abstractmethod
    def draw(self):
        pass

class ConfigComponentBase(ComponentBase):
    @abc.abstractmethod
    def load_model(self, model):
        pass

    @abc.abstractmethod
    def get_model(self):
        pass