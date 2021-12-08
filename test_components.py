import PyQt5
import servicemanager
import testing_utils
import hypertts
import constants
import component_voiceselection

class EmptyDialog(PyQt5.QtWidgets.QDialog):
    def __init__(self):
        super(PyQt5.QtWidgets.QDialog, self).__init__()

    def setupUi(self):
        self.main_layout = PyQt5.QtWidgets.QVBoxLayout(self)

    def getLayout(self):
        return self.main_layout

def test_voice_selection(qtbot):
    manager = servicemanager.ServiceManager(testing_utils.get_test_services_dir(), 'test_services')
    manager.init_services()
    manager.get_service('ServiceA').set_enabled(True)
    manager.get_service('ServiceB').set_enabled(True)
    anki_utils = testing_utils.MockAnkiUtils({})

    hypertts_instance = hypertts.HyperTTS(anki_utils, manager)

    dialog = EmptyDialog()
    dialog.setupUi()

    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance)
    voiceselection.draw(dialog.getLayout())

    # ensure filters are set to All by default
    assert voiceselection.audio_languages_combobox.currentText() == constants.LABEL_FILTER_ALL
    assert voiceselection.languages_combobox.currentText() == constants.LABEL_FILTER_ALL
    assert voiceselection.services_combobox.currentText() == constants.LABEL_FILTER_ALL
    assert voiceselection.genders_combobox.currentText() == constants.LABEL_FILTER_ALL

    # filter language to Japanese
    voiceselection.languages_combobox.setCurrentText('Japanese')

    # ensure japanese filter is enabled
    assert len(voiceselection.filtered_voice_list) < len(voiceselection.voice_list)
    assert len(voiceselection.filtered_voice_list) == voiceselection.voices_combobox.count()
    for voice in voiceselection.filtered_voice_list:
        assert voice.language.lang == constants.Language.ja


    # dialog.exec_()
