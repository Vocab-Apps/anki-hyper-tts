import os
import unittest

from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import servicemanager
from hypertts_addon import voice
from hypertts_addon.services import voicelist


def services_dir():
    current_script_path = os.path.realpath(__file__)
    current_script_dir = os.path.dirname(current_script_path)
    root_dir = os.path.join(current_script_dir, '..')
    hypertts_dir = os.path.join(root_dir, constants.DIR_HYPERTTS_ADDON)
    return os.path.join(hypertts_dir, constants.DIR_SERVICES)


class GeminiIntegrationTests(unittest.TestCase):
    def test_generated_voicelist_has_no_gemini_entries(self):
        self.assertFalse(any(voice_entry.service == 'Gemini' for voice_entry in voicelist.VOICE_LIST))

    def test_service_manager_locates_gemini_voice_from_current_and_legacy_voice_ids(self):
        manager = servicemanager.ServiceManager(
            services_dir(),
            f'{constants.DIR_HYPERTTS_ADDON}.{constants.DIR_SERVICES}',
            False,
        )
        manager.init_services()

        gemini = manager.get_service('Gemini')
        self.assertEqual(gemini.configuration_options(), {'project_id': str})
        self.assertEqual(gemini.configuration_display_name(), 'Gemini (Cloud TTS)')

        gemini.enabled = True
        gemini_voices = manager.full_voice_list(single_service_name='Gemini')
        kore_locale_voice = next(
            voice_entry for voice_entry in gemini_voices
            if voice_entry.name == 'Kore' and voice_entry.voice_key['language_code'] == 'cmn-tw'
        )

        serialized_voice_id = voice.serialize_voice_id_v3(kore_locale_voice.voice_id)
        self.assertEqual(
            serialized_voice_id,
            {
                'service': 'Gemini',
                'voice_key': {'voice_name': 'Kore', 'language_code': 'cmn-tw'},
            },
        )

        round_trip_voice_id = voice.deserialize_voice_id_v3(serialized_voice_id)
        self.assertEqual(
            manager.locate_voice(round_trip_voice_id).voice_key,
            {'voice_name': 'Kore', 'language_code': 'cmn-tw'},
        )

        legacy_name_voice_id = voice.TtsVoiceId_v3(service='Gemini', voice_key={'name': 'Kore'})
        legacy_language_voice_id = voice.TtsVoiceId_v3(
            service='Gemini',
            voice_key={'voice_name': 'Kore', 'language_code': 'en-US'},
        )

        self.assertEqual(manager.locate_voice(legacy_name_voice_id).voice_key['voice_name'], 'Kore')
        self.assertEqual(
            manager.locate_voice(legacy_language_voice_id).voice_key,
            {'voice_name': 'Kore', 'language_code': 'en-us'},
        )
        self.assertEqual(kore_locale_voice.audio_languages, [languages.AudioLanguage.zh_TW])
