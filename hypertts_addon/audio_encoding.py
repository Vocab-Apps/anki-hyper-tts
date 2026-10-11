"""Local audio encoding helpers.

Some services return lossless audio (raw PCM or WAV) that has to be turned into an mp3
before it is written to the collection: the Gemini API only returns PCM/WAV, and the
Google service requests lossless LINEAR16 for AudioFormat.mp3_hq because its native mp3
is a fixed 32 kbps on Chirp 3 HD voices.

Encoding goes through the lame binary bundled with Anki, located the same way
aqt.sound._encode_mp3 does it. We don't call aqt.sound._encode_mp3 itself because it
doesn't let us pick the bitrate, and lame's default for 24 kHz mono input is 32 kbps.
"""
import io
import os
import re
import wave
import tempfile
import subprocess

import aqt.sound
import aqt.utils

from hypertts_addon import constants
from hypertts_addon import errors
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)

RIFF_HEADER = b'RIFF'


def wrap_pcm_in_wav(pcm_bytes: bytes, sample_rate: int, num_channels: int = 1, sample_width: int = 2) -> bytes:
    """Wrap headerless PCM in a WAV container."""
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(num_channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_bytes)
    return buffer.getvalue()


def ensure_wav(audio_bytes: bytes, mime_type: str, default_sample_rate: int) -> bytes:
    """Return WAV bytes for an audio response which is either WAV already, or headerless
    16-bit mono PCM (mime type audio/L16;codec=pcm;rate=24000), whose sample rate is taken
    from the mime type when present."""
    if audio_bytes.startswith(RIFF_HEADER):
        return audio_bytes
    sample_rate = default_sample_rate
    rate_match = re.search(r'rate=(\d+)', mime_type or '')
    if rate_match:
        sample_rate = int(rate_match.group(1))
    logger.debug(f'wrapping headerless PCM ({mime_type}) in a WAV container at {sample_rate} Hz')
    return wrap_pcm_in_wav(audio_bytes, sample_rate)


def encode_wav_to_mp3(wav_bytes: bytes, bitrate_kbps: int = constants.AUDIO_MP3_HQ_ENCODE_BITRATE_KBPS) -> bytes:
    """Encode WAV audio to a constant bitrate mp3 and return the mp3 bytes."""
    wav_fh, wav_path = tempfile.mkstemp(prefix='hypertts_encode_', suffix='.wav')
    os.close(wav_fh)
    mp3_fh, mp3_path = tempfile.mkstemp(prefix='hypertts_encode_', suffix='.mp3')
    os.close(mp3_fh)
    try:
        with open(wav_path, 'wb') as f:
            f.write(wav_bytes)
        run_lame(wav_path, mp3_path, bitrate_kbps)
        with open(mp3_path, 'rb') as f:
            return f.read()
    finally:
        for path in (wav_path, mp3_path):
            if os.path.exists(path):
                os.remove(path)


def run_lame(wav_path: str, mp3_path: str, bitrate_kbps: int):
    # same invocation as aqt.sound._encode_mp3, plus the bitrate
    cmd = ['lame', wav_path, mp3_path, '--noreplaygain', '--quiet', '-b', str(bitrate_kbps)]
    cmd, env = aqt.sound._packagedCmd(cmd)
    logger.debug(f'encoding mp3 at {bitrate_kbps} kbps: {cmd}')
    try:
        process = subprocess.Popen(cmd, startupinfo=aqt.utils.startup_info(), env=env)
        retcode = aqt.sound.retryWait(process)
    except Exception as e:
        raise errors.AudioEncodingError(f'could not run {" ".join(cmd)}: {e}') from e
    if retcode != 0:
        raise errors.AudioEncodingError(f'{" ".join(cmd)} returned {retcode}')
