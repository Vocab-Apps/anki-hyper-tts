import io
import wave
import math
import struct
import unittest

import magic

from hypertts_addon import constants
from hypertts_addon import errors
from hypertts_addon import audio_encoding


def build_wav_bytes(duration_seconds=0.5, sample_rate=24000):
    # a 440 Hz tone, 16-bit mono
    frames = b''.join(struct.pack('<h', int(8000 * math.sin(2 * math.pi * 440 * i / sample_rate)))
                      for i in range(int(duration_seconds * sample_rate)))
    return audio_encoding.wrap_pcm_in_wav(frames, sample_rate), frames


class AudioEncodingTests(unittest.TestCase):

    def test_encode_wav_to_mp3_default_bitrate(self):
        # pytest tests/test_audio_encoding.py -k test_encode_wav_to_mp3_default_bitrate
        # anki's own encoder would produce 32 kbps for 24 kHz mono input
        wav_bytes, _ = build_wav_bytes()
        mp3_bytes = audio_encoding.encode_wav_to_mp3(wav_bytes)
        file_type = magic.from_buffer(mp3_bytes)
        self.assertIn('MPEG ADTS, layer III', file_type)
        self.assertIn(f'{constants.AUDIO_MP3_HQ_ENCODE_BITRATE_KBPS} kbps', file_type)
        self.assertIn('24 kHz', file_type)
        self.assertIn('Monaural', file_type)

    def test_encode_wav_to_mp3_explicit_bitrate(self):
        wav_bytes, _ = build_wav_bytes()
        mp3_bytes = audio_encoding.encode_wav_to_mp3(wav_bytes, bitrate_kbps=64)
        self.assertIn('64 kbps', magic.from_buffer(mp3_bytes))

    def test_encode_invalid_wav_raises(self):
        with self.assertRaises(errors.AudioEncodingError):
            audio_encoding.encode_wav_to_mp3(b'this is not a wav file')

    def test_ensure_wav_passthrough(self):
        wav_bytes, _ = build_wav_bytes()
        self.assertEqual(audio_encoding.ensure_wav(wav_bytes, 'audio/wav', 24000), wav_bytes)

    def test_ensure_wav_wraps_headerless_pcm(self):
        _, frames = build_wav_bytes(sample_rate=16000)
        wav_bytes = audio_encoding.ensure_wav(frames, 'audio/L16;codec=pcm;rate=16000', 24000)
        with wave.open(io.BytesIO(wav_bytes), 'rb') as wav:
            self.assertEqual(wav.getframerate(), 16000)
            self.assertEqual(wav.getnchannels(), 1)
            self.assertEqual(wav.getsampwidth(), 2)
            self.assertEqual(wav.getnframes(), len(frames) // 2)

    def test_ensure_wav_default_sample_rate(self):
        _, frames = build_wav_bytes()
        wav_bytes = audio_encoding.ensure_wav(frames, '', 24000)
        with wave.open(io.BytesIO(wav_bytes), 'rb') as wav:
            self.assertEqual(wav.getframerate(), 24000)
