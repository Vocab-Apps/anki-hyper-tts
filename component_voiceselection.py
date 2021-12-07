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

        languages = set()
        audio_languages = set()
        services = set()
        genders = set()

        for voice in voice_list:
            audio_languages.add(voice.language)
            languages.add(voice.language.lang)
            services.add(voice.service.name)
            genders.add(voice.gender)

        audio_language_combobox = PyQt5.QtWidgets.QComboBox()
        audio_language_combobox.addItems([audio_lang.audio_lang_name for audio_lang in audio_languages])
        layout.addWidget(audio_language_combobox)

        for voice in voice_list:
            self.draw_voice(layout, voice)

    def draw_voice(self, layout, voice):
        layout.addWidget(PyQt5.QtWidgets.QLabel(voice.name))