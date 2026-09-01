import io
import sys
import types
import wave
import unittest
from unittest import mock

# audio_utils imports hypertts_addon (which skips the anki import under pytest)
if not hasattr(sys, '_pytest_mode'):
    sys._pytest_mode = True
from hypertts_addon import audio_utils


class TestPcmToWavBytes(unittest.TestCase):

    def test_wraps_pcm_in_riff_wav(self):
        pcm = b'\x00\x01' * 100
        data = audio_utils.pcm_to_wav_bytes(pcm, sample_rate=24000)
        self.assertEqual(data[:4], b'RIFF')
        self.assertEqual(data[8:12], b'WAVE')
        with wave.open(io.BytesIO(data)) as w:
            self.assertEqual(w.getnchannels(), 1)
            self.assertEqual(w.getsampwidth(), 2)
            self.assertEqual(w.getframerate(), 24000)
            self.assertEqual(w.readframes(w.getnframes()), pcm)


class TestEncodeWavToMp3(unittest.TestCase):
    """Verify the lame command is built with the requested bitrate, without
    needing a real Anki install or lame binary."""

    def test_invokes_lame_with_bitrate(self):
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured['cmd'] = cmd
            with open(cmd[2], 'wb') as f:  # cmd[2] is the mp3 destination path
                f.write(b'FAKEMP3')
            proc = mock.Mock()
            proc.wait.return_value = 0
            return proc

        fake_sound = types.ModuleType('aqt.sound')
        fake_sound._packagedCmd = lambda c: (c, {})
        fake_sound.retryWait = lambda p: p.wait()
        fake_utils = types.ModuleType('aqt.utils')
        fake_utils.startup_info = lambda: None
        fake_aqt = types.ModuleType('aqt')
        fake_aqt.sound = fake_sound
        fake_aqt.utils = fake_utils

        with mock.patch.dict('sys.modules', {'aqt': fake_aqt, 'aqt.sound': fake_sound, 'aqt.utils': fake_utils}), \
             mock.patch('hypertts_addon.audio_utils.subprocess.Popen', side_effect=fake_popen):
            out = audio_utils.encode_wav_to_mp3(b'RIFFxxxxWAVE', 128)

        self.assertEqual(out, b'FAKEMP3')
        self.assertEqual(captured['cmd'][0], 'lame')
        self.assertIn('-b', captured['cmd'])
        self.assertIn('128', captured['cmd'])
        self.assertIn('--quiet', captured['cmd'])

    def test_missing_lame_raises_clear_error(self):
        # On Linux without lame installed, Popen raises FileNotFoundError; this
        # must surface as an actionable HyperTTSError (not a raw OSError, which
        # would be mis-reported to Sentry as a crash).
        from hypertts_addon import errors

        def fake_popen(cmd, **kwargs):
            raise FileNotFoundError(2, 'No such file or directory', 'lame')

        fake_sound = types.ModuleType('aqt.sound')
        fake_sound._packagedCmd = lambda c: (c, {})
        fake_sound.retryWait = lambda p: p.wait()
        fake_utils = types.ModuleType('aqt.utils')
        fake_utils.startup_info = lambda: None
        fake_aqt = types.ModuleType('aqt')
        fake_aqt.sound = fake_sound
        fake_aqt.utils = fake_utils

        with mock.patch.dict('sys.modules', {'aqt': fake_aqt, 'aqt.sound': fake_sound, 'aqt.utils': fake_utils}), \
             mock.patch('hypertts_addon.audio_utils.subprocess.Popen', side_effect=fake_popen):
            with self.assertRaises(errors.Mp3EncoderNotFound) as ctx:
                audio_utils.encode_wav_to_mp3(b'RIFFxxxxWAVE', 128)
        self.assertIn('lame', str(ctx.exception).lower())
        self.assertIsInstance(ctx.exception, errors.HyperTTSError)

    def test_raises_when_lame_fails(self):
        def fake_popen(cmd, **kwargs):
            proc = mock.Mock()
            proc.wait.return_value = 1  # non-zero exit
            return proc

        fake_sound = types.ModuleType('aqt.sound')
        fake_sound._packagedCmd = lambda c: (c, {})
        fake_sound.retryWait = lambda p: p.wait()
        fake_utils = types.ModuleType('aqt.utils')
        fake_utils.startup_info = lambda: None
        fake_aqt = types.ModuleType('aqt')
        fake_aqt.sound = fake_sound
        fake_aqt.utils = fake_utils

        with mock.patch.dict('sys.modules', {'aqt': fake_aqt, 'aqt.sound': fake_sound, 'aqt.utils': fake_utils}), \
             mock.patch('hypertts_addon.audio_utils.subprocess.Popen', side_effect=fake_popen):
            with self.assertRaises(Exception):
                audio_utils.encode_wav_to_mp3(b'RIFFxxxxWAVE', 128)


if __name__ == '__main__':
    unittest.main()
