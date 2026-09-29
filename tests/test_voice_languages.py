"""choosing the language of a multilingual voice: one voice per language, in every service"""

from unittest import mock

import aqt.qt
import dataclasses

from test_utils import gui_testing_utils

from hypertts_addon import cloudlanguagetools
from hypertts_addon import component_voiceselection
from hypertts_addon import component_voiceselection_easy
from hypertts_addon import config_models
from hypertts_addon import constants
from hypertts_addon import context
from hypertts_addon import hypertts
from hypertts_addon import voice as voice_module
from hypertts_addon.languages import AudioLanguage
from hypertts_addon.services import service_azure
from hypertts_addon.services import service_dwds
from hypertts_addon.services import service_gemini
from hypertts_addon.services import service_openai


def get_hypertts_instance_with_multilingual_voices():
    hypertts_instance = gui_testing_utils.get_hypertts_instance()
    hypertts_instance.service_manager.get_service('ServiceD').enabled = True
    return hypertts_instance


def draw_voice_selection(hypertts_instance):
    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection.VoiceSelection(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())
    return dialog, voiceselection


def find_voice(hypertts_instance, voice_key):
    return [v for v in hypertts_instance.service_manager.full_voice_list() if v.voice_key == voice_key][0]


def test_saved_setting_without_a_box_survives_resave_and_is_shown(qtbot):
    # a preset saved while alloy still had a language box; the box has since been removed
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    dialog, voiceselection = draw_voice_selection(hypertts_instance)
    alloy = find_voice(hypertts_instance, {'name': 'alloy'})
    model = config_models.VoiceSelectionSingle()
    model.set_voice(config_models.VoiceWithOptions(alloy.voice_id, {'speed': 1.5, 'language_code': 'es-MX'}))

    voiceselection.load_model(model)
    assert voiceselection.serialize()['voice']['options'] == {'speed': 1.5, 'language_code': 'es-MX'}
    # the user edits a setting that still has a box
    dialog.findChild(aqt.qt.QDoubleSpinBox, 'voice_option_speed').setValue(2.0)

    assert voiceselection.serialize()['voice']['options'] == {'speed': 2.0, 'language_code': 'es-MX'}
    saved_line = dialog.findChild(aqt.qt.QLabel, 'voice_option_saved_language_code')
    assert saved_line is not None, 'the kept setting must be visible'
    assert saved_line.text() == 'language_code: es-MX'


def test_opening_another_preset_on_the_same_voice_replaces_its_settings(qtbot):
    # "Open preset" three times on one voice: the old preset twice, then a plain one
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    dialog, voiceselection = draw_voice_selection(hypertts_instance)
    alloy = find_voice(hypertts_instance, {'name': 'alloy'})
    old_preset = config_models.VoiceSelectionSingle()
    old_preset.set_voice(config_models.VoiceWithOptions(alloy.voice_id, {'speed': 1.5, 'language_code': 'es-MX'}))
    plain_preset = config_models.VoiceSelectionSingle()
    plain_preset.set_voice(config_models.VoiceWithOptions(alloy.voice_id, {}))

    voiceselection.load_model(old_preset)
    voiceselection.load_model(old_preset)
    assert len(dialog.findChildren(aqt.qt.QLabel, 'voice_option_saved_language_code')) == 1

    voiceselection.load_model(plain_preset)
    assert voiceselection.serialize()['voice']['options'] == {}
    assert dialog.findChild(aqt.qt.QDoubleSpinBox, 'voice_option_speed').value() == 1.0
    assert dialog.findChildren(aqt.qt.QLabel, 'voice_option_saved_language_code') == []


def test_opening_a_preset_on_the_shown_voice_while_filtered_keeps_that_voice(qtbot):
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    dialog, voiceselection = draw_voice_selection(hypertts_instance)
    voiceselection.services_combobox.setCurrentText('ServiceD')
    voiceselection.audio_languages_combobox.setCurrentText('Spanish (Mexico)')
    voiceselection.voices_combobox.setCurrentText('Multilingual, Female, alloy (ServiceD)')
    alloy = find_voice(hypertts_instance, {'name': 'alloy'})
    preset = config_models.VoiceSelectionSingle()
    preset.set_voice(config_models.VoiceWithOptions(alloy.voice_id, {'speed': 1.5}))

    voiceselection.load_model(preset)

    assert voiceselection.services_combobox.currentText() == 'ServiceD'
    assert voiceselection.audio_languages_combobox.currentText() == 'Spanish (Mexico)'
    assert voiceselection.voices_combobox.currentText() == 'Multilingual, Female, alloy (ServiceD)'
    assert dialog.findChild(aqt.qt.QDoubleSpinBox, 'voice_option_speed').value() == 1.5
    assert voiceselection.serialize()['voice'] == {'voice_id': {'service': 'ServiceD', 'voice_key': {'name': 'alloy'}}, 'options': {'speed': 1.5}}

def test_opening_a_preset_while_filters_match_nothing_keeps_its_settings(qtbot):
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    dialog, voiceselection = draw_voice_selection(hypertts_instance)
    voiceselection.services_combobox.setCurrentText('ServiceD')
    voiceselection.audio_languages_combobox.setCurrentText('Japanese')
    alloy = find_voice(hypertts_instance, {'name': 'alloy'})
    preset = config_models.VoiceSelectionSingle()
    preset.set_voice(config_models.VoiceWithOptions(alloy.voice_id, {'speed': 1.5}))

    voiceselection.load_model(preset)

    assert voiceselection.serialize()['voice']['options'] == {'speed': 1.5}
    assert [l for l in dialog.findChildren(aqt.qt.QLabel) if l.objectName().startswith('voice_option_saved_')] == [], 'speed has a box'


def test_editing_after_opening_a_preset_leaves_the_preset_itself_unchanged(qtbot):
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    dialog, voiceselection = draw_voice_selection(hypertts_instance)
    alloy = find_voice(hypertts_instance, {'name': 'alloy'})
    preset = config_models.VoiceSelectionSingle()
    preset.set_voice(config_models.VoiceWithOptions(alloy.voice_id, {'speed': 1.5, 'language_code': 'es-MX'}))

    voiceselection.load_model(preset)
    dialog.findChild(aqt.qt.QDoubleSpinBox, 'voice_option_speed').setValue(2.0)

    assert preset.voice.options == {'speed': 1.5, 'language_code': 'es-MX'}
    assert voiceselection.serialize()['voice']['options'] == {'speed': 2.0, 'language_code': 'es-MX'}


def test_opening_a_preset_keeps_a_setting_saved_at_its_default_value(qtbot):
    # e.g. a Gemini language_code typed back to en-US: the value is saved, and it is part of the cache key
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    dialog, voiceselection = draw_voice_selection(hypertts_instance)
    alloy = find_voice(hypertts_instance, {'name': 'alloy'})
    preset = config_models.VoiceSelectionSingle()
    preset.set_voice(config_models.VoiceWithOptions(alloy.voice_id, {'speed': 1.0}))

    voiceselection.load_model(preset)
    assert voiceselection.serialize()['voice']['options'] == {'speed': 1.0}
    voiceselection.load_model(preset)
    assert voiceselection.serialize()['voice']['options'] == {'speed': 1.0}


def test_random_list_shows_a_saved_setting_without_a_box(qtbot):
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    dialog, voiceselection = draw_voice_selection(hypertts_instance)
    alloy = find_voice(hypertts_instance, {'name': 'alloy'})
    random_preset = config_models.VoiceSelectionRandom()
    random_preset.add_voice(config_models.VoiceWithOptionsRandom(alloy.voice_id, {'language_code': 'es-MX'}))

    voiceselection.load_model(random_preset)

    listed = [voiceselection.voice_list_grid_layout.itemAt(i).widget().text()
              for i in range(voiceselection.voice_list_grid_layout.count())
              if isinstance(voiceselection.voice_list_grid_layout.itemAt(i).widget(), aqt.qt.QLabel)]
    assert listed == ['Multilingual, Female, alloy (ServiceD) (language_code: es-MX)']


# the voice list: one voice per language
# ======================================

def gemini_kore():
    return [v for v in service_gemini.Gemini().voice_list() if v.voice_key == {'name': 'Kore'}][0]


def test_expand_languages_leaves_a_one_language_voice_alone():
    google_like_voice = voice_module.TtsVoice_v3(
        name='es-US-Chirp-HD-F', voice_key={'name': 'es-US-Chirp-HD-F', 'language_code': 'es-US'}, options={},
        service='Google', gender=constants.Gender.Female, audio_languages=[AudioLanguage.es_US],
        service_fee=constants.ServiceFee.paid)
    assert voice_module.expand_languages(google_like_voice) == [google_like_voice]


def test_expand_languages_adds_one_voice_per_language():
    kore = gemini_kore()
    expanded = voice_module.expand_languages(kore)

    assert len(kore.audio_languages) == 87
    assert len(expanded) == 1 + 87
    assert expanded[0] is kore, 'the multilingual voice itself stays listed, unchanged'
    assert kore.voice_key == {'name': 'Kore'}
    assert 'language_code' in kore.options
    kore_mexico = [v for v in expanded if v.audio_languages == [AudioLanguage.es_MX]]
    assert len(kore_mexico) == 1
    assert kore_mexico[0].voice_key == {'name': 'Kore', 'audio_language': 'es_MX'}
    assert str(kore_mexico[0]) == 'Spanish (Mexico), Female, Kore (Firm) (Gemini)'
    assert 'language_code' not in kore_mexico[0].options, 'the chosen language supersedes the free-text box'
    assert set(kore_mexico[0].options) == {'model', 'prompt', 'format'}
    # no copy for a language Kore does not list
    assert [v for v in expanded if v.audio_languages == [AudioLanguage.es_US]] == []


def test_only_voices_that_can_be_told_a_language_are_listed_per_language(qtbot):
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    voice_keys = [v.voice_key for v in hypertts_instance.service_manager.full_voice_list(single_service_name='ServiceD')]

    assert voice_keys == [
        {'name': 'Kore'},
        {'name': 'Kore', 'audio_language': 'es_ES'},
        {'name': 'Kore', 'audio_language': 'es_MX'},
        {'name': 'Kore', 'audio_language': 'fr_FR'},
        {'name': 'alloy'},
    ]


def test_a_language_listed_twice_gets_one_entry():
    xiaoxiao = [v for v in service_azure.Azure().voice_list()
                if v.voice_key['name'] == 'Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoDialectsNeural)'][0]
    assert xiaoxiao.audio_languages.count(AudioLanguage.zh_CN_shaanxi) == 2

    shaanxi = [v for v in voice_module.expand_languages(xiaoxiao) if v.audio_languages == [AudioLanguage.zh_CN_shaanxi]]

    assert len(shaanxi) == 1


def test_openai_voices_keep_only_their_multilingual_entry():
    openai = service_openai.OpenAI()
    multilingual = [v for v in openai.voice_list() if len(v.audio_languages) > 1]
    assert multilingual != []
    assert not any(openai.can_send_audio_language(v) for v in multilingual)


def test_chosen_audio_language():
    kore = gemini_kore()
    kore_mexico = [v for v in voice_module.expand_languages(kore) if v.audio_languages == [AudioLanguage.es_MX]][0]

    assert voice_module.get_chosen_audio_language(kore_mexico) == AudioLanguage.es_MX
    assert voice_module.get_chosen_audio_language(kore) is None
    assert voice_module.get_chosen_audio_language(service_dwds.DigitalesWorterbuchDeutschenSprache().voice_list()[0]) is None
    # the language written into {{tts}} tags and sent with VocabAI requests
    assert voice_module.get_audio_language_for_voice(kore_mexico) == AudioLanguage.es_MX
    assert voice_module.get_audio_language_for_voice(kore) == AudioLanguage.en_US


def test_tts_tag_carries_the_chosen_language(qtbot):
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    def realtime_side(voice_key):
        voice_selection = config_models.VoiceSelectionSingle()
        voice_selection.set_voice(config_models.VoiceWithOptions(voice_module.TtsVoiceId_v3(voice_key=voice_key, service='ServiceD'), {}))
        side = config_models.RealtimeConfigSide()
        side.side_enabled = True
        side.source = config_models.RealtimeSourceAnkiTTS()
        side.source.field_name = 'Spanish'
        side.source.field_type = constants.AnkiTTSFieldType.Regular
        side.voice_selection = voice_selection
        return side

    per_language_tag = hypertts_instance.build_realtime_tts_tag(realtime_side({'name': 'Kore', 'audio_language': 'es_MX'}), 'Front_realtime_0')
    multilingual_tag = hypertts_instance.build_realtime_tts_tag(realtime_side({'name': 'Kore'}), 'Front_realtime_0')

    assert per_language_tag == '{{tts es_MX hypertts_preset=Front_realtime_0 voices=HyperTTS:Spanish}}'
    assert multilingual_tag == '{{tts en_US hypertts_preset=Front_realtime_0 voices=HyperTTS:Spanish}}'


def test_old_preset_cache_key_is_unchanged():
    # computed on main (05007b9), before voices were listed per language:
    # HyperTTS.get_hash_for_audio_request(None, '¿Dónde está la biblioteca?',
    #     TtsVoiceId_v3(voice_key={'name': 'Kore'}, service='Gemini'), {'language_code': 'es-MX'})
    old_preset_voice_id = voice_module.TtsVoiceId_v3(voice_key={'name': 'Kore'}, service='Gemini')
    hash_str = hypertts.HyperTTS.get_hash_for_audio_request(None, '¿Dónde está la biblioteca?', old_preset_voice_id, {'language_code': 'es-MX'})
    assert hash_str == 'd569a35f0d387468472ff2d8518affd90b0b6ecbc25f981accc4ebad'


def test_old_and_per_language_voice_keys_are_both_found(qtbot):
    service_manager = get_hypertts_instance_with_multilingual_voices().service_manager

    old = service_manager.locate_voice(voice_module.TtsVoiceId_v3(voice_key={'name': 'Kore'}, service='ServiceD'))
    mexico = service_manager.locate_voice(voice_module.TtsVoiceId_v3(voice_key={'name': 'Kore', 'audio_language': 'es_MX'}, service='ServiceD'))

    assert len(old.audio_languages) == 3
    assert mexico.audio_languages == [AudioLanguage.es_MX]


# the voice screen
# ================

KORE_MEXICO = 'Spanish (Mexico), Female, Kore (Firm) (ServiceD)'

def test_locale_filter_lists_per_language_entries(qtbot):
    dialog, voiceselection = draw_voice_selection(get_hypertts_instance_with_multilingual_voices())

    voiceselection.services_combobox.setCurrentText('ServiceD')
    voiceselection.audio_languages_combobox.setCurrentText('Spanish (Mexico)')

    entries = [voiceselection.voices_combobox.itemText(i) for i in range(voiceselection.voices_combobox.count())]
    assert entries == [
        'Multilingual, Female, Kore (Firm) (ServiceD)',
        'Multilingual, Female, alloy (ServiceD)',
        KORE_MEXICO,
    ]


def test_per_language_entries_are_listed_only_while_a_language_filter_is_set(qtbot):
    dialog, voiceselection = draw_voice_selection(get_hypertts_instance_with_multilingual_voices())
    voiceselection.services_combobox.setCurrentText('ServiceD')
    entries = lambda: [voiceselection.voices_combobox.itemText(i) for i in range(voiceselection.voices_combobox.count())]

    assert entries() == ['Multilingual, Female, Kore (Firm) (ServiceD)', 'Multilingual, Female, alloy (ServiceD)']
    voiceselection.languages_combobox.setCurrentText('Spanish')
    assert entries() == ['Multilingual, Female, Kore (Firm) (ServiceD)', 'Multilingual, Female, alloy (ServiceD)',
                         KORE_MEXICO, 'Spanish (Spain), Female, Kore (Firm) (ServiceD)']


def test_opening_an_old_preset_selects_its_voice(qtbot):
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    dialog, voiceselection = draw_voice_selection(hypertts_instance)
    kore = find_voice(hypertts_instance, {'name': 'Kore'})
    preset = config_models.VoiceSelectionSingle()
    preset.set_voice(config_models.VoiceWithOptions(kore.voice_id, {'language_code': 'es-MX'}))

    voiceselection.load_model(preset)

    assert voiceselection.voices_combobox.currentText() == 'Multilingual, Female, Kore (Firm) (ServiceD)'
    assert voiceselection.serialize()['voice']['voice_id']['voice_key'] == {'name': 'Kore'}


def test_opening_a_preset_whose_voice_the_filters_hide_clears_the_filters(qtbot):
    # github issue #290
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    dialog, voiceselection = draw_voice_selection(hypertts_instance)
    voiceselection.languages_combobox.setCurrentText('French')
    alloy = find_voice(hypertts_instance, {'name': 'alloy'})
    preset = config_models.VoiceSelectionSingle()
    preset.set_voice(config_models.VoiceWithOptions(alloy.voice_id, {'speed': 1.5}))

    voiceselection.load_model(preset)

    assert voiceselection.languages_combobox.currentIndex() == 0
    assert voiceselection.voices_combobox.currentText() == 'Multilingual, Female, alloy (ServiceD)'
    assert voiceselection.serialize()['voice']['options'] == {'speed': 1.5}


def test_choosing_a_per_language_entry_saves_it_without_a_language_box(qtbot):
    dialog, voiceselection = draw_voice_selection(get_hypertts_instance_with_multilingual_voices())
    voiceselection.languages_combobox.setCurrentText('Spanish')

    voiceselection.voices_combobox.setCurrentText(KORE_MEXICO)

    assert dialog.findChild(aqt.qt.QLineEdit, 'voice_option_language_code') is None
    assert dialog.findChild(aqt.qt.QLineEdit, 'voice_option_prompt') is not None
    assert voiceselection.serialize()['voice']['voice_id'] == {
        'service': 'ServiceD', 'voice_key': {'name': 'Kore', 'audio_language': 'es_MX'}}


def test_play_sample_sends_the_chosen_language(qtbot):
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    dialog, voiceselection = draw_voice_selection(hypertts_instance)
    voiceselection.sample_text_selected('¿Dónde está la biblioteca?')
    voiceselection.languages_combobox.setCurrentText('Spanish')

    voiceselection.voices_combobox.setCurrentText(KORE_MEXICO)
    voiceselection.play_sample()

    requested = hypertts_instance.service_manager.get_service('ServiceD').requested_audio
    assert requested['chosen_audio_language'] == 'es_MX'
    assert requested['source_text'] == '¿Dónde está la biblioteca?'


def test_loading_a_per_language_preset_selects_that_entry(qtbot):
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    dialog, voiceselection = draw_voice_selection(hypertts_instance)
    kore_mexico_id = voice_module.TtsVoiceId_v3(voice_key={'name': 'Kore', 'audio_language': 'es_MX'}, service='ServiceD')
    model = config_models.VoiceSelectionSingle()
    model.set_voice(config_models.VoiceWithOptions(kore_mexico_id, {'model': 'model-hd', 'prompt': 'habla despacio'}))

    voiceselection.load_model(model)

    assert voiceselection.languages_combobox.currentText() == 'Spanish', 'the entry is shown by the Language filter'
    assert voiceselection.voices_combobox.currentText() == KORE_MEXICO
    assert voiceselection.serialize()['voice']['options'] == {'model': 'model-hd', 'prompt': 'habla despacio'}


def test_random_add_voice_keeps_the_language(qtbot):
    dialog, voiceselection = draw_voice_selection(get_hypertts_instance_with_multilingual_voices())
    voiceselection.radio_button_random.setChecked(True)
    voiceselection.languages_combobox.setCurrentText('Spanish')

    voiceselection.voices_combobox.setCurrentText(KORE_MEXICO)
    qtbot.mouseClick(voiceselection.add_voice_button, aqt.qt.Qt.MouseButton.LeftButton)

    serialized = voiceselection.serialize()
    assert [entry['voice_id']['voice_key'] for entry in serialized['voice_list']] == [{'name': 'Kore', 'audio_language': 'es_MX'}]
    listed = [voiceselection.voice_list_grid_layout.itemAt(i).widget().text()
              for i in range(voiceselection.voice_list_grid_layout.count())
              if isinstance(voiceselection.voice_list_grid_layout.itemAt(i).widget(), aqt.qt.QLabel)]
    assert listed == [KORE_MEXICO]


def test_easy_mode_offers_per_language_entries(qtbot):
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection_easy.VoiceSelectionEasy(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())

    voiceselection.languages_combobox.setCurrentText('Spanish')
    voiceselection.services_combobox.setCurrentText('ServiceD')
    voiceselection.voices_combobox.setCurrentText(KORE_MEXICO)

    assert voiceselection.serialize()['voice']['voice_id']['voice_key'] == {'name': 'Kore', 'audio_language': 'es_MX'}


def test_easy_mode_opens_a_per_language_preset(qtbot):
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    voiceselection = component_voiceselection_easy.VoiceSelectionEasy(hypertts_instance, dialog, gui_testing_utils.MockModelChangeCallback().model_updated)
    dialog.addChildWidget(voiceselection.draw())
    preset = config_models.VoiceSelectionSingle()
    preset.set_voice(config_models.VoiceWithOptions(voice_module.TtsVoiceId_v3(voice_key={'name': 'Kore', 'audio_language': 'es_MX'}, service='ServiceD'), {}))

    voiceselection.load_model(preset)

    assert voiceselection.languages_combobox.currentText() == 'Spanish'
    assert voiceselection.voices_combobox.currentText() == KORE_MEXICO


def test_voice_screen_opens_a_preset_of_a_voice_keyed_by_a_plain_string(qtbot):
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    service_a_class = type(hypertts_instance.service_manager.get_service('ServiceA'))
    service_a_voice_list = service_a_class.voice_list
    german = dataclasses.replace(service_dwds.DigitalesWorterbuchDeutschenSprache().voice_list()[0], service='ServiceA')
    with mock.patch.object(service_a_class, 'voice_list', lambda self: service_a_voice_list(self) + [german]):
        dialog, voiceselection = draw_voice_selection(hypertts_instance)
        voiceselection.languages_combobox.setCurrentText('Spanish')
        preset = config_models.VoiceSelectionSingle()
        preset.set_voice(config_models.VoiceWithOptions(german.voice_id, {}))

        voiceselection.load_model(preset)

    assert voiceselection.languages_combobox.currentIndex() == 0
    assert voiceselection.voices_combobox.currentText() == 'German (Germany), Female, German (ServiceA)'
    assert voiceselection.serialize()['voice']['voice_id']['voice_key'] == 'german'


def test_easy_mode_selects_its_default_voice(qtbot):
    hypertts_instance = get_hypertts_instance_with_multilingual_voices()
    dialog = gui_testing_utils.EmptyDialog()
    dialog.setupUi()
    model_change_callback = gui_testing_utils.MockModelChangeCallback()
    voiceselection = component_voiceselection_easy.VoiceSelectionEasy(hypertts_instance, dialog, model_change_callback.model_updated)
    dialog.addChildWidget(voiceselection.draw())
    # the test services have no Azure: stand in alloy for Azure's Jenny Multilingual
    alloy = find_voice(hypertts_instance, {'name': 'alloy'})
    with mock.patch.object(hypertts_instance.service_manager, 'locate_voice', return_value=alloy) as locate_voice:
        voiceselection.pick_default_voice()

    locate_voice.assert_called_once_with(voice_module.TtsVoiceId_v3(
        voice_key={'name': 'Microsoft Server Speech Text to Speech Voice (en-US, JennyMultilingualNeural)'}, service='Azure'))
    assert voiceselection.voices_combobox.currentText() == 'Multilingual, Female, alloy (ServiceD)'
    assert model_change_callback.model.voice.voice_id == alloy.voice_id


# the VocabAI request
# ===================

def make_vocabai_client():
    clt = cloudlanguagetools.CloudLanguageTools()
    clt.config = mock.Mock()
    clt.config.use_vocabai_api = True
    clt.config.hypertts_pro_api_key = 'test_key'
    clt.config.user_uuid = 'test_uuid'
    clt.config.vocabai_api_url_override = None
    clt.disable_ssl_verification = False
    return clt


def send_vocabai_request(voice, options):
    with mock.patch('requests.Session.post', return_value=mock.Mock(status_code=200, content=b'audio')) as post:
        make_vocabai_client().get_tts_audio('¿Dónde está la biblioteca?', voice, options,
            context.AudioRequestContext(constants.AudioRequestReason.preview))
    return post.call_args.kwargs['json']


def test_vocabai_request_carries_the_chosen_language_in_options():
    kore_mexico = [v for v in voice_module.expand_languages(gemini_kore()) if v.audio_languages == [AudioLanguage.es_MX]][0]
    options = {'model': 'gemini-2.5-pro-tts'}

    sent = send_vocabai_request(kore_mexico, options)

    assert kore_mexico.voice_key == {'name': 'Kore', 'audio_language': 'es_MX'}, 'the voice itself is not changed'
    assert options == {'model': 'gemini-2.5-pro-tts'}, 'the caller\'s options are not changed (they feed the cache key)'

    assert sent['voice_key'] == {'name': 'Kore'}, 'the voice_key as the server lists it'
    assert sent['options'] == {'model': 'gemini-2.5-pro-tts', 'audio_language': 'es_MX'}
    assert sent['language_code'] == 'es'


def test_vocabai_request_for_a_multilingual_voice_is_unchanged():
    sent = send_vocabai_request(gemini_kore(), {'language_code': 'es-MX'})

    assert sent['voice_key'] == {'name': 'Kore'}
    assert sent['options'] == {'language_code': 'es-MX'}
    assert sent['language_code'] == 'en'
