import io
import os
import wave
import tempfile
import subprocess

from hypertts_addon import errors
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)


def pcm_to_wav_bytes(pcm_bytes, sample_rate, channels=1, sample_width=2):
    """Wrap raw little-endian PCM samples in a WAV (RIFF) container in memory."""
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()


def encode_wav_to_mp3(wav_bytes, bitrate_kbps):
    """Encode WAV audio to MP3 at a fixed CBR bitrate using Anki's bundled lame.

    Anki's own aqt.sound._encode_mp3 invokes lame with no bitrate argument, so
    it falls back to lame's default (32 kbps for a 24 kHz mono source). We want
    a specific, higher bitrate, so we build the lame command ourselves and reuse
    Anki's helpers to resolve the bundled binary (_packagedCmd) and to run it
    (retryWait / startup_info).
    """
    import aqt.sound
    import aqt.utils

    wav_fh, wav_path = tempfile.mkstemp(prefix='hypertts_', suffix='.wav')
    os.close(wav_fh)
    mp3_fh, mp3_path = tempfile.mkstemp(prefix='hypertts_', suffix='.mp3')
    os.close(mp3_fh)
    try:
        with open(wav_path, 'wb') as f:
            f.write(wav_bytes)
        cmd = ['lame', wav_path, mp3_path, '--noreplaygain', '--quiet', '-b', str(bitrate_kbps)]
        cmd, env = aqt.sound._packagedCmd(cmd)
        try:
            process = subprocess.Popen(cmd, startupinfo=aqt.utils.startup_info(), env=env)
        except FileNotFoundError as e:
            # The lame binary is bundled on Windows/macOS but may be absent on
            # Linux. Surface an actionable, non-retryable HyperTTSError instead
            # of a raw OSError (which would be mis-reported to Sentry as a crash).
            logger.warning(f'lame mp3 encoder not found: {e}')
            raise errors.Mp3EncoderNotFound() from e
        retcode = aqt.sound.retryWait(process)
        if retcode != 0:
            raise Exception(f'lame mp3 encoding failed (exit code {retcode}) for command: {" ".join(cmd)}')
        with open(mp3_path, 'rb') as f:
            return f.read()
    finally:
        for path in (wav_path, mp3_path):
            try:
                os.remove(path)
            except OSError:
                pass
