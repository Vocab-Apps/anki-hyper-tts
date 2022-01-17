import PyQt5

import component_common
import component_source


class ComponentBatch(component_common.ConfigComponentBase):
    def __init__(self, hypertts, note_id_list):
        self.hypertts = hypertts
        self.note_id_list = note_id_list

        self.source = component_source.BatchSource(self.hypertts, self.note_id_list)

    def load_model(self, model):
        pass

    def get_model(self):
        return None

    def draw(self, layout):
        self.tabs = PyQt5.QtWidgets.QTabWidget()
        self.tab_source = PyQt5.QtWidgets.QWidget()
        self.tab_target = PyQt5.QtWidgets.QWidget()

        self.tab_source.setLayout(self.source.draw())
        # self.source.draw(self.tab_source.layout)

        self.tabs.addTab(self.tab_source, 'Source')
        self.tabs.addTab(self.tab_target, 'Target')

        layout.addWidget(self.tabs)