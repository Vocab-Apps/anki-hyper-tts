"""Request helpers shared by the ElevenLabs and ElevenLabsCustom services."""
import requests

from hypertts_addon import constants
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)

# output formats, https://elevenlabs.io/docs/api-reference/text-to-speech/convert
# 192 kbps mp3 matches the quality of the opus path, but "MP3 with 192kbps bitrate
# requires you to be subscribed to Creator tier or above"
MP3_OUTPUT_FORMAT = 'mp3_44100_192'
MP3_OUTPUT_FORMAT_FALLBACK = 'mp3_44100_128'
OGG_OPUS_OUTPUT_FORMAT = 'opus_48000_192'

OUTPUT_FORMAT_MAP = {
    'mp3': MP3_OUTPUT_FORMAT,
    'ogg_opus': OGG_OPUS_OUTPUT_FORMAT,
}


def get_output_format(audio_format_str):
    return OUTPUT_FORMAT_MAP.get(audio_format_str, MP3_OUTPUT_FORMAT)


def is_output_format_rejected(response):
    """Whether an error response complains about the requested output_format, which is what
    we expect for an account whose subscription tier doesn't allow 192 kbps mp3."""
    if response.status_code not in (400, 402, 403):
        return False
    body = (response.text or '').lower()
    return 'output_format' in body or MP3_OUTPUT_FORMAT in body


def post_with_output_format_fallback(url, output_format, data, headers):
    """POST the synthesis request with the given output_format, retrying once at the
    fallback mp3 bitrate when the account's tier rejects the 192 kbps mp3."""
    response = requests.post(f'{url}?output_format={output_format}', json=data, headers=headers,
        timeout=constants.RequestTimeout)
    if output_format == MP3_OUTPUT_FORMAT and is_output_format_rejected(response):
        logger.warning(f'ElevenLabs rejected output_format {output_format} '
            f'(HTTP {response.status_code}: {response.text}), retrying with {MP3_OUTPUT_FORMAT_FALLBACK}')
        response = requests.post(f'{url}?output_format={MP3_OUTPUT_FORMAT_FALLBACK}', json=data, headers=headers,
            timeout=constants.RequestTimeout)
    return response
