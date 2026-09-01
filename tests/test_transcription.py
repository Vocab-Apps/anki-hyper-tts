import base64
import unittest
from unittest.mock import MagicMock, patch

from hypertts_addon import constants
from hypertts_addon import transcription
from hypertts_addon.languages import AudioLanguage
from hypertts_addon import voice as voice_module
from hypertts_addon.services.service_elevenlabs import ElevenLabs
from hypertts_addon.services.service_google import Google


class TranscriptionTests(unittest.TestCase):
    def test_character_alignment_to_segments(self):
        segments = transcription.character_alignment_to_segments(
            list('Hello world'),
            [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.8, 0.9, 1.0, 1.1],
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.5, 0.8, 0.9, 1.0, 1.1, 1.2],
        )

        self.assertEqual(transcription.serialize_segments(segments), '[{"s":0,"e":0.5,"w":"Hello"},{"s":0.7,"e":1.2,"w":"world"}]')

    def test_build_marked_ssml(self):
        marked_text = transcription.build_marked_ssml('Hello <world>')

        self.assertEqual(marked_text.words, ['Hello', '<world>'])
        self.assertEqual(marked_text.ssml, '<speak><mark name="w0"/>Hello <mark name="w1"/>&lt;world&gt; <mark name="w2"/></speak>')

    def test_google_timepoints_to_segments(self):
        segments = transcription.google_timepoints_to_segments(
            ['Hello', 'world'],
            [
                {'markName': 'w0', 'timeSeconds': 0},
                {'markName': 'w1', 'timeSeconds': 0.4},
                {'markName': 'w2', 'timeSeconds': 0.9},
            ],
        )

        self.assertEqual(transcription.serialize_segments(segments), '[{"s":0,"e":0.4,"w":"Hello"},{"s":0.4,"e":0.9,"w":"world"}]')


class TranscriptServiceTests(unittest.TestCase):
    def test_elevenlabs_get_tts_audio_transcript(self):
        service = ElevenLabs()
        service.configure({'api_key': 'fake_key'})
        mock_voice = self.make_elevenlabs_voice()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            'audio_base64': base64.b64encode(b'audio').decode('ascii'),
            'alignment': {
                'characters': list('Hi there'),
                'character_start_times_seconds': [0, 0.1, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8],
                'character_end_times_seconds': [0.1, 0.2, 0.2, 0.5, 0.6, 0.7, 0.8, 0.9],
            },
        }

        with patch('hypertts_addon.services.service_elevenlabs.requests.post', return_value=response) as post:
            result = service.get_tts_audio_transcript('Hi there', mock_voice, {})

        self.assertEqual(result.audio, b'audio')
        self.assertEqual(result.transcript_json, '[{"s":0,"e":0.2,"w":"Hi"},{"s":0.4,"e":0.9,"w":"there"}]')
        self.assertIn('/with-timestamps', post.call_args.args[0])

    def test_google_get_tts_audio_transcript(self):
        service = Google()
        service.configure({'api_key': 'fake_key'})
        mock_voice = self.make_google_voice()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            'audioContent': base64.b64encode(b'audio').decode('ascii'),
            'timepoints': [
                {'markName': 'w0', 'timeSeconds': 0},
                {'markName': 'w1', 'timeSeconds': 0.3},
                {'markName': 'w2', 'timeSeconds': 0.8},
            ],
        }

        with patch('hypertts_addon.services.service_google.requests.post', return_value=response) as post:
            result = service.get_tts_audio_transcript('Hi there', mock_voice, {})

        payload = post.call_args.kwargs['json']
        self.assertEqual(result.audio, b'audio')
        self.assertEqual(result.transcript_json, '[{"s":0,"e":0.3,"w":"Hi"},{"s":0.3,"e":0.8,"w":"there"}]')
        self.assertEqual(payload['enableTimePointing'], ['SSML_MARK'])
        self.assertIn('<mark name="w0"/>Hi', payload['input']['ssml'])

    def make_elevenlabs_voice(self):
        return voice_module.TtsVoice_v3(
            name='Test Voice',
            voice_key={'voice_id': 'test_id', 'model_id': 'eleven_monolingual_v1'},
            options={
                'stability': {'default': 0.5},
                'similarity_boost': {'default': 0.75},
            },
            service='ElevenLabs',
            gender=constants.Gender.Male,
            audio_languages=[AudioLanguage.en_US],
            service_fee=constants.ServiceFee.paid,
        )

    def make_google_voice(self):
        return voice_module.TtsVoice_v3(
            name='en-US voice',
            voice_key={'language_code': 'en-US', 'name': 'en-US-Neural2-A'},
            options={'speaking_rate': {'default': 1.0}},
            service='Google',
            gender=constants.Gender.Female,
            audio_languages=[AudioLanguage.en_US],
            service_fee=constants.ServiceFee.paid,
        )
