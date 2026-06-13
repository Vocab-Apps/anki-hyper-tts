import os
import json
import math
import wave
import base64
import tempfile
import requests
import aqt.sound


from hypertts_addon import voice as voice_module
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import options
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)

# Gemini speech-generation REST API:
#   https://ai.google.dev/gemini-api/docs/speech-generation#rest
# Model catalogue (ListModels):
#   https://ai.google.dev/api/models#method:-models.list
# Prebuilt voice names and supported languages:
#   https://ai.google.dev/gemini-api/docs/speech-generation#voices

# The model names exposed in voicelist.py follow the Google Cloud Text-to-Speech
# API naming (e.g. 'gemini-2.5-flash-tts'), but this service calls the Gemini API
# directly, which uses different IDs (e.g. 'gemini-2.5-flash-preview-tts', as
# returned by ListModels). Translate voice-list names to Gemini API model IDs here.
MODEL_NAME_MAP = {
    'gemini-2.5-flash-tts': 'gemini-2.5-flash-preview-tts',
    'gemini-2.5-pro-tts': 'gemini-2.5-pro-preview-tts',
}

DEFAULT_RETRY_AFTER_SECONDS = 60

# Gemini can return HTTP 200 with *no audio* when it refuses to synthesize the
# input. The refusal shows up either as a top-level promptFeedback.blockReason
# or as a candidate finishReason that is not a normal completion. These are
# permanent rejections of the specific input text — retrying the identical
# request will always fail — so they must be raised as a permanent error, not
# retried. See https://ai.google.dev/api/generate-content for the enums.
GEMINI_BLOCK_FINISH_REASONS = {
    'SAFETY',
    'PROHIBITED_CONTENT',
    'BLOCKLIST',
    'SPII',
    'RECITATION',
    'IMAGE_SAFETY',
    # 'OTHER' is Gemini's catch-all terminal state. For TTS, observed events
    # (Sentry ANKI-HYPER-TTS-HT9) consistently fail for the same input text
    # with usageMetadata reporting tokens were consumed but no audio produced
    # — i.e. the model refused this specific input. Treat as permanent so the
    # batch processor stops retrying.
    'OTHER',
}


def _extract_retry_after_seconds(response_text):
    try:
        data = json.loads(response_text)
        for detail in data['error']['details']:
            if detail.get('@type', '').endswith('google.rpc.RetryInfo'):
                delay = detail['retryDelay']
                return max(1, math.ceil(float(delay.rstrip('s'))))
    except Exception:
        pass
    return DEFAULT_RETRY_AFTER_SECONDS


def _raise_for_error_status(status_code, response_text, source_text, voice):
    # Map a non-OK Gemini response to the appropriate ServiceRequestError
    # subclass. Caller handles 200 (success) and 429 (rate-limit-with-
    # Retry-After) before reaching here.
    #
    # Previously this site raised the legacy errors.RequestError for every
    # non-200 response, which is not retry-aware — so a permanent 403
    # ("User location is not supported for the API use", Sentry
    # ANKI-HYPER-TTS-K4V) was retried 3× and grouped under the legacy class
    # instead of being surfaced as a permanent permission error.
    try:
        data = json.loads(response_text)
        error_message = data.get('error', {}).get('message', str(data))
    except (ValueError, TypeError, AttributeError):
        error_message = response_text or f'HTTP {status_code}'

    full_msg = f'Gemini API error (HTTP {status_code}): {error_message}'

    if status_code == 400:
        # INVALID_ARGUMENT — bad/unsupported input
        raise errors.ServiceInputError(source_text, voice, full_msg)
    if status_code in (401, 403):
        # UNAUTHENTICATED / PERMISSION_DENIED — bad key, regional restriction
        raise errors.ServicePermissionError(source_text, voice, full_msg)
    if status_code == 404:
        # NOT_FOUND — model not available to this key
        raise errors.ServicePermissionError(source_text, voice, full_msg)
    if 500 <= status_code < 600:
        # 5xx — upstream/server-side failure
        raise errors.ServiceGatewayError(source_text, voice, full_msg)
    raise errors.UnknownServiceError(source_text, voice, full_msg)


class Gemini(service.ServiceBase):
    CONFIG_API_KEY = 'api_key'

    def __init__(self):
        service.ServiceBase.__init__(self)

    def cloudlanguagetools_enabled(self):
        return True

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.paid

    def configuration_options(self):
        return {
            self.CONFIG_API_KEY: str,
        }

    def voice_list(self):
        return self.basic_voice_list()

    def get_tts_audio(self, source_text, voice: voice_module.VoiceBase, voice_options):
        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)

        model = voice_options.get('model', voice.options['model']['default'])
        api_model = MODEL_NAME_MAP.get(model, model)
        prompt = voice_options.get('prompt', voice.options['prompt']['default'])
        language_code = voice_options.get('language_code', voice.options['language_code']['default'])

        audio_format_str = voice_options.get(options.AUDIO_FORMAT_PARAMETER, options.AudioFormat.mp3.name)
        audio_format = options.AudioFormat[audio_format_str]

        if audio_format != options.AudioFormat.mp3:
            raise errors.ServiceInputError(source_text, voice,
                f'Gemini service only supports mp3 output; {audio_format.name} is not supported')

        text = f'{prompt}: {source_text}' if prompt else source_text

        speech_config = {
            'voiceConfig': {
                'prebuiltVoiceConfig': {'voiceName': voice.voice_key['name']}
            }
        }
        if language_code:
            speech_config['languageCode'] = language_code

        payload = {
            'contents': [{'parts': [{'text': text}]}],
            'generationConfig': {
                'responseModalities': ['AUDIO'],
                'speechConfig': speech_config,
            },
            'model': api_model,
        }

        logger.debug(f'requesting audio with payload {payload}')

        response = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/{api_model}:generateContent',
            headers={
                'x-goog-api-key': api_key,
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=constants.RequestTimeout,
        )

        if response.status_code == 429:
            logger.warning(f'HTTP {response.status_code}, body: {response.text}')
            retry_after = _extract_retry_after_seconds(response.text)
            logger.warning(f'retry_after: {retry_after}')
            raise errors.RateLimitRetryAfterError(
                source_text, voice,
                f'Gemini rate limit: {response.status_code} {response.text}',
                retry_after,
            )

        if response.status_code != 200:
            logger.warning(f'HTTP {response.status_code}, headers: {dict(response.headers)}, body: {response.text}')
            _raise_for_error_status(response.status_code, response.text, source_text, voice)

        data = response.json()

        # Detect a content-policy refusal before trying to read the audio.
        # Observed in the wild as a 200 response with body
        # {'promptFeedback': {'blockReason': 'PROHIBITED_CONTENT'}, ...}
        # (Sentry ANKI-HYPER-TTS-HT9). Previously this fell through to the
        # generic KeyError handler below and was raised as the legacy,
        # non-retry-aware RequestError, so it was endlessly retried and
        # mis-grouped in triage. It is a permanent rejection of this input
        # text, so raise the permanent ServiceInputError instead.
        block_reason = data.get('promptFeedback', {}).get('blockReason')
        if block_reason:
            raise errors.ServiceInputError(source_text, voice,
                f'Gemini refused to generate audio (blockReason: {block_reason}): {data}')
        candidates = data.get('candidates') or []
        if candidates:
            finish_reason = candidates[0].get('finishReason')
            if finish_reason in GEMINI_BLOCK_FINISH_REASONS:
                raise errors.ServiceInputError(source_text, voice,
                    f'Gemini refused to generate audio (finishReason: {finish_reason}): {data}')

        try:
            encoded = data['candidates'][0]['content']['parts'][0]['inlineData']['data']
        except (KeyError, IndexError):
            raise errors.RequestError(source_text, voice, f'Gemini returned no audio: {data}')

        pcm_bytes = base64.b64decode(encoded)

        return self._encode_pcm_to_mp3(pcm_bytes)

    def _encode_pcm_to_mp3(self, pcm_bytes):
        # Gemini returns raw signed little-endian PCM at 24kHz / 16-bit / mono.
        # Per PCM_TO_MP3.md: wrap the bytes in a WAV container via stdlib `wave`,
        # then hand off to Anki's bundled `lame` via aqt.sound._encode_mp3.
        wav_fh, wav_path = tempfile.mkstemp(prefix='hypertts_gemini_', suffix='.wav')
        os.close(wav_fh)
        mp3_fh, mp3_path = tempfile.mkstemp(prefix='hypertts_gemini_', suffix='.mp3')
        os.close(mp3_fh)
        try:
            with wave.open(wav_path, 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(24000)
                w.writeframes(pcm_bytes)
            aqt.sound._encode_mp3(wav_path, mp3_path)
            with open(mp3_path, 'rb') as f:
                return f.read()
        finally:
            for p in (wav_path, mp3_path):
                if os.path.exists(p):
                    os.remove(p)
