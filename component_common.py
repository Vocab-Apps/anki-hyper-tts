import abc

class ComponentBase(abc.ABC):
    @abc.abstractmethod
    def draw(self, layout):
        pass

class ConfigComponentBase(ComponentBase):
    @abc.abstractmethod
    def load_model(self, model):
        pass

    @abc.abstractmethod
    def get_model(self):
        pass