import PyQt5

class VoiceSelection():
    def __init__(self, hypertts):
        self.hypertts = hypertts

    def draw(self, layout):
        # filters:
        # - language
        # - locale
        # - service
        # - gender

        # 1. get full voice list
        # 2. iterate over the list, gather attributes
        # 3. populate filters
        # 4. draw all voices

        voice_list = self.hypertts.service_manager.full_voice_list()
        for voice in voice_list:
            self.draw_voice(layout, voice)

    def draw_voice(self, layout, voice):
        layout.addWidget(PyQt5.QtWidgets.QLabel(voice.name))