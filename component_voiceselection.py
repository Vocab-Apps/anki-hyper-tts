import PyQt5
import constants

class VoiceSelection():
    def __init__(self, hypertts):
        self.hypertts = hypertts

    def get_voices(self):
        self.voice_list = self.hypertts.service_manager.full_voice_list()

        languages = set()
        audio_languages = set()
        services = set()
        genders = set()

        for voice in self.voice_list:
            audio_languages.add(voice.language)
            languages.add(voice.language.lang)
            services.add(voice.service.name)
            genders.add(voice.gender)

        self.audio_languages = list(audio_languages)
        self.languages = list(languages)
        self.services = list(services)
        self.genders = list(genders)

    def populate_combobox(self, combobox, items):
        combobox.addItem(constants.LABEL_FILTER_ALL)
        combobox.insertSeparator(1)
        combobox.addItems(items)

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


        self.get_voices()

        self.voices_layout = PyQt5.QtWidgets.QVBoxLayout()
        layout.addLayout(self.voices_layout)

        self.audio_languages_combobox = PyQt5.QtWidgets.QComboBox()
        self.languages_combobox = PyQt5.QtWidgets.QComboBox()
        self.services_combobox = PyQt5.QtWidgets.QComboBox()
        self.genders_combobox = PyQt5.QtWidgets.QComboBox()
        self.voices_combobox = PyQt5.QtWidgets.QComboBox()

        self.populate_combobox(self.audio_languages_combobox, [audio_lang.audio_lang_name for audio_lang in self.audio_languages])
        self.populate_combobox(self.languages_combobox, [language.lang_name for language in self.languages])
        self.populate_combobox(self.services_combobox, self.services)
        self.populate_combobox(self.genders_combobox, [gender.name for gender in self.genders])

        self.voices_layout.addWidget(self.audio_languages_combobox)
        self.voices_layout.addWidget(self.languages_combobox)
        self.voices_layout.addWidget(self.services_combobox)
        self.voices_layout.addWidget(self.genders_combobox)
        self.voices_layout.addWidget(self.voices_combobox)

        self.audio_languages_combobox.currentIndexChanged.connect(self.filter_and_draw_voices)
        self.languages_combobox.currentIndexChanged.connect(self.filter_and_draw_voices)
        self.services_combobox.currentIndexChanged.connect(self.filter_and_draw_voices)
        self.genders_combobox.currentIndexChanged.connect(self.filter_and_draw_voices)

        self.filter_and_draw_voices(0)


    def filter_and_draw_voices(self, current_index):
        self.draw_all_voices(self.voice_list)

    def draw_all_voices(self, voice_list):
        self.voices_combobox.clear()
        self.voices_combobox.addItems([voice.name for voice in voice_list])
