import copy

import pytest

from hypertts_addon import component_batch, component_realtime, component_voiceselection, component_voiceselection_easy
from hypertts_addon import config_models, constants
from test_utils import gui_testing_utils, testing_utils


@pytest.mark.parametrize('selection_class', [config_models.VoiceSelectionSingle,
    config_models.VoiceSelectionRandom, config_models.VoiceSelectionPriority])
def test_filter_configuration_roundtrip(selection_class):
    hypertts = gui_testing_utils.get_hypertts_instance()
    selected = hypertts.service_manager.full_voice_list()[0]
    model = selection_class()
    if isinstance(model, config_models.VoiceSelectionSingle):
        model.voice = config_models.VoiceWithOptions(selected.voice_id, {'speed': 42})
    elif isinstance(model, config_models.VoiceSelectionRandom):
        model.add_voice(config_models.VoiceWithOptionsRandom(selected.voice_id, {}, 3))
    else:
        model.add_voice(config_models.VoiceWithOptionsPriority(selected.voice_id, {}))
    legacy = model.serialize()
    assert 'filters' not in legacy
    assert hypertts.deserialize_voice_selection(legacy).filters == config_models.VoiceFilters()
    model.filters = config_models.VoiceFilters(language='fr', audio_language='fr_FR',
                                             service='ServiceA', gender='Male')
    assert hypertts.deserialize_voice_selection(model.serialize()).serialize() == model.serialize()


def build_component(qtbot, easy=False):
    hypertts = gui_testing_utils.get_hypertts_instance()
    dialog = gui_testing_utils.build_empty_dialog()
    qtbot.addWidget(dialog)
    changes = []
    cls = component_voiceselection_easy.VoiceSelectionEasy if easy else component_voiceselection.VoiceSelection
    component = cls(hypertts, dialog, lambda model: changes.append(copy.deepcopy(model)))
    dialog.addChildWidget(component.draw())
    changes.clear()
    return hypertts, component, changes


@pytest.mark.parametrize('easy', [False, True])
@pytest.mark.parametrize('conflicting', [False, True])
@pytest.mark.parametrize('rate', [1.0, 3.5])
def test_restore_filters_voice_and_options(qtbot, easy, conflicting, rate):
    hypertts, component, changes = build_component(qtbot, easy)
    selected = next(v for v in component.voice_list if v.name == 'voice_a_2')
    model = config_models.VoiceSelectionSingle()
    model.voice = config_models.VoiceWithOptions(selected.voice_id, {'speaking_rate': rate})
    model.filters = config_models.VoiceFilters(service='ServiceB' if conflicting else selected.service,
        language=selected.audio_languages[0].lang.name,
        audio_language=selected.audio_languages[0].name, gender=selected.gender.name)
    saved = model.serialize()
    component.load_model(hypertts.deserialize_voice_selection(saved))
    assert not changes
    assert component.serialize() == saved
    assert component.voices_combobox.currentText() == str(selected)
    assert component.read_filters() == model.filters
    if not easy:
        assert component.voice_options_widgets['voice_option_speaking_rate'].value() == rate
    # Reload the component's own model, which must not lose its options during redraw.
    existing = component.get_model()
    component.load_model(existing)
    assert component.serialize() == saved
    assert existing.serialize() == saved
    legacy = copy.deepcopy(model)
    legacy.filters = config_models.VoiceFilters()
    component.load_model(legacy)
    assert component.read_filters() == config_models.VoiceFilters()
    assert component.serialize() == legacy.serialize()
    assert not changes


@pytest.mark.parametrize('mode', ['random', 'priority'])
def test_multiple_filters_notify_restore_and_reset(qtbot, mode):
    _, component, changes = build_component(qtbot)
    getattr(component, f'radio_button_{mode}').setChecked(True)
    component.services_combobox.setCurrentText('ServiceA')
    component.add_voice()
    component.voices_combobox.setCurrentIndex(1)
    component.add_voice()
    if mode == 'random':
        component.get_model().set_random_weight(0, 7)
    model = copy.deepcopy(component.get_model())
    component.services_combobox.setCurrentText('ServiceB')
    assert changes[-1].filters.service == 'ServiceB'
    changes.clear()
    component.load_model(model)
    assert not changes
    assert component.serialize() == model.serialize()
    component.reset_filters()
    assert changes[-1].filters == config_models.VoiceFilters()
    assert component.get_model().voice_list[0].serialize() == model.voice_list[0].serialize()
    component.services_combobox.setCurrentText('ServiceA')
    component.radio_button_single.setChecked(True)
    assert component.get_model().filters.service == 'ServiceA'


def test_realtime_filter_save_reopen(qtbot):
    generator = testing_utils.TestConfigGenerator()
    hypertts = generator.build_hypertts_instance_test_servicemanager('default')
    dialog = gui_testing_utils.build_empty_dialog()
    qtbot.addWidget(dialog)
    realtime = component_realtime.ComponentRealtime(hypertts, dialog, 0)
    realtime.configure_note(hypertts.anki_utils.get_note_by_id(generator.note_id_1))
    realtime.draw(dialog.getLayout())
    realtime.front.side_enabled_checkbox.setChecked(True)
    realtime.front.source.source_field_combobox.setCurrentText('English')
    realtime.front.voice_selection.services_combobox.setCurrentText('ServiceB')
    realtime.back.side_enabled_checkbox.setChecked(True)
    realtime.back.source.source_field_combobox.setCurrentText('Chinese')
    realtime.back.voice_selection.services_combobox.setCurrentText('ServiceA')
    expected = realtime.get_model().serialize()
    key = hypertts.save_realtime_config(realtime.get_model(), None)
    loaded = hypertts.load_realtime_config(key)
    realtime.front.voice_selection.reset_filters()
    realtime.load_model(loaded)
    assert realtime.front.voice_selection.read_filters().service == 'ServiceB'
    assert realtime.back.voice_selection.read_filters().service == 'ServiceA'
    assert realtime.get_model().serialize() == expected


def test_unavailable_filters_and_exception_callback_state(qtbot):
    _, component, changes = build_component(qtbot)
    model = copy.deepcopy(component.get_model())
    model.filters = config_models.VoiceFilters(service='removed', language='unknown')
    component.load_model(model)
    assert component.read_filters() == config_models.VoiceFilters()
    assert model.filters == config_models.VoiceFilters()
    assert not changes
    model.voice = None
    with pytest.raises(AttributeError):
        component.load_model(model)
    assert component.enable_model_change_callback


def test_batch_filter_only_change_save_reopen(qtbot):
    generator = testing_utils.TestConfigGenerator()
    hypertts = generator.build_hypertts_instance_test_servicemanager('default')

    def interact(dialog):
        batch = dialog.batch_component
        batch.profile_save_button.click()
        assert not batch.profile_save_button.isEnabled()
        batch.voice_selection.radio_button_random.setChecked(True)
        batch.voice_selection.add_voice()
        batch.profile_save_button.click()
        batch.voice_selection.services_combobox.setCurrentText('ServiceB')
        assert batch.profile_save_button.isEnabled()
        batch.profile_save_button.click()
        preset_id = batch.get_model().uuid
        batch.voice_selection.reset_filters()
        batch.load_preset(preset_id)
        assert batch.voice_selection.read_filters().service == 'ServiceB'
        assert not batch.profile_save_button.isEnabled()

    hypertts.anki_utils.dialog_input_fn_map[constants.DIALOG_ID_BATCH] = interact
    component_batch.create_component_batch_browser_new_preset(hypertts,
        [generator.note_id_1, generator.note_id_2], 'Filter preset')
