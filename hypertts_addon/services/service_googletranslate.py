import sys
import time
import gtts
import io
import requests
from typing import List

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import logging_utils
logger = logging_utils.get_child_logger(__name__)


lang = languages.AudioLanguage
LANGUAGE_KEY_MAP = {
    'id': lang.id_ID,
    'is': lang.is_IS,
    'iw': lang.he_IL,
    'pt': lang.pt_PT,
    'pt-PT': lang.pt_PT,
    'fr-CA': lang.fr_CA,
    'sr': lang.sr_RS,
    'zh-CN': lang.zh_CN,
    'zh': lang.zh_CN,
    'zh-TW': lang.zh_TW,
}

GENDER_MAP = {
    'ko': constants.Gender.Male
}

# Regional voice variants. gTTS exposes a single language code (e.g. "pt", "en", "fr") via
# tts_langs(), but the underlying Google Translate API produces different accents depending
# on the top-level domain ("translate.google.<tld>"). For languages with multiple useful
# accents we emit one voice per voice_key below, each routed to the right tld.
#
# The (lang, tld) pairings below mirror the table in the gTTS docs for localized accents:
# https://gtts.readthedocs.io/en/latest/module.html#localized-accents
#
# Backward compatibility: every voice_key that the OLD voice_list() emitted is preserved
# here so existing saved presets continue to resolve. The OLD voice_list() iterated
# gtts.lang.tts_langs() directly — at the time of writing that returns 'en', 'fr', 'fr-CA',
# 'pt', 'pt-PT', 'es' (and many others). All of those are still emitted; their tld is now
# corrected so the audio matches the AudioLanguage label.
#
# Notably for issue #346: 'pt' and 'pt-PT' were both legacy voice_keys labelled Portuguese
# (Portugal) but routed to tld='com' (Brazilian audio). Both now route to tld='pt'.
# Similarly 'fr-CA' was emitted by gTTS but silently fell back to lang='fr' (France audio);
# it now routes to tld='ca' for actual Canadian audio.
#
# voice_key -> (gtts_lang, tld, AudioLanguage)
EXPLICIT_VOICES = {
    # English (issue #297 adds the regional variants beyond 'en')
    'en':    ('en', 'us',     lang.en_US),
    'en-GB': ('en', 'co.uk',  lang.en_GB),
    'en-AU': ('en', 'com.au', lang.en_AU),
    'en-CA': ('en', 'ca',     lang.en_CA),
    'en-IN': ('en', 'co.in',  lang.en_IN),
    'en-IE': ('en', 'ie',     lang.en_IE),
    'en-ZA': ('en', 'co.za',  lang.en_ZA),
    'en-NG': ('en', 'com.ng', lang.en_NG),
    # French
    'fr':    ('fr', 'fr',     lang.fr_FR),
    'fr-CA': ('fr', 'ca',     lang.fr_CA),
    # Portuguese — 'pt' and 'pt-PT' are both legacy keys, both route to Portugal audio.
    # 'pt-BR' is the new Brazilian voice (issue #346).
    'pt':    ('pt', 'pt',     lang.pt_PT),
    'pt-PT': ('pt', 'pt',     lang.pt_PT),
    'pt-BR': ('pt', 'com.br', lang.pt_BR),
    # Spanish
    'es':    ('es', 'es',     lang.es_ES),
    'es-MX': ('es', 'com.mx', lang.es_MX),
    'es-US': ('es', 'us',     lang.es_US),
}

# When iterating gTTS's tts_langs(), if a gtts key appears here, emit the listed voice_keys
# (in this order) instead of using the generic single-voice-per-gtts-key path. Each listed
# voice_key must exist in EXPLICIT_VOICES.
GTTS_KEY_TO_EMITTED_VOICE_KEYS = {
    'en':    ['en', 'en-GB', 'en-AU', 'en-CA', 'en-IN', 'en-IE', 'en-ZA', 'en-NG'],
    'fr':    ['fr'],
    'fr-CA': ['fr-CA'],
    'pt':    ['pt', 'pt-BR'],
    'pt-PT': ['pt-PT'],
    'es':    ['es', 'es-MX', 'es-US'],
}

class GoogleTranslate(service.ServiceBase):
    CONFIG_THROTTLE_SECONDS = 'throttle_seconds'

    def __init__(self):
        service.ServiceBase.__init__(self)

    def configuration_options(self):
        return {
            self.CONFIG_THROTTLE_SECONDS: float
        }

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.free

    def get_language(self, language_key):
        # check if we have this language in AudioLanguageDefaults
        if language_key in languages.Language.__members__:
            language = languages.Language[language_key]
            if language in languages.AudioLanguageDefaults:
                return languages.AudioLanguageDefaults[language]
        # do we have an override for this language
        if language_key in LANGUAGE_KEY_MAP:
            return LANGUAGE_KEY_MAP[language_key]
        return None

    def voice_list(self) -> List[voice.TtsVoice_v3]:
        gtts_languages = gtts.lang.tts_langs()
        voices = []
        for language_key, language_name in gtts_languages.items():
            gender = GENDER_MAP.get(language_key, constants.Gender.Female)
            if language_key in GTTS_KEY_TO_EMITTED_VOICE_KEYS:
                for voice_key in GTTS_KEY_TO_EMITTED_VOICE_KEYS[language_key]:
                    _, _, audio_language = EXPLICIT_VOICES[voice_key]
                    voices.append(voice.build_voice_v3(
                        name=audio_language.audio_lang_name,
                        gender=gender,
                        language=audio_language,
                        service=self,
                        voice_key=voice_key,
                        options={}
                    ))
                continue
            language = self.get_language(language_key)
            if language == None:
                logger.error(f'{self.name}: could not process language {language_key}')
            else:
                voices.append(voice.build_voice_v3(
                    name=language_name,
                    gender=gender,
                    language=language,
                    service=self,
                    voice_key=language_key,
                    options={}
                ))
        return voices

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, options):
        # configuration options
        throttle_seconds = self.get_configuration_value_optional(self.CONFIG_THROTTLE_SECONDS, 0)

        if throttle_seconds > 0:
            time.sleep(throttle_seconds)

        # Resolve voice_key to (gtts_lang, tld). Voice keys not in EXPLICIT_VOICES
        # (the long-tail of single-accent languages) pass straight through with tld='com'.
        explicit = EXPLICIT_VOICES.get(voice.voice_key)
        if explicit is not None:
            gtts_lang, tld, _ = explicit
        else:
            gtts_lang, tld = voice.voice_key, 'com'

        logger.info(f'gtts.gTTS request: voice_key={voice.voice_key!r}, lang={gtts_lang!r}, '
                    f'tld={tld!r}, timeout={constants.RequestTimeout}, text={source_text!r}')

        try:
            tts = gtts.gTTS(text=source_text, lang=gtts_lang, tld=tld, timeout=constants.RequestTimeout)
            buffer = io.BytesIO()
            tts.write_to_fp(buffer)

            return buffer.getbuffer()
        except gtts.gTTSError as e:
            headers = e.rsp.headers if e.rsp is not None else None
            logger.warning(f'Google Translate error: {e}, headers: {headers}')
            if e.rsp is not None:
                status_code = e.rsp.status_code
                if status_code == 429:
                    retry_after = int(e.rsp.headers.get('Retry-After', 30))
                    raise errors.RateLimitRetryAfterError(source_text, voice, str(e), retry_after) from e
                if status_code in (502, 503, 504):
                    raise errors.ServiceGatewayError(source_text, voice, str(e)) from e
            # gTTS wraps the underlying requests exception via implicit chaining
            underlying = e.__cause__ or e.__context__
            if isinstance(underlying, requests.exceptions.Timeout):
                raise errors.ServiceTimeoutError(source_text, voice, 'HTTP request timed out') from e
            # ChunkedEncodingError inherits from RequestException (not ConnectionError) but
            # signals a transport-level break mid-response — e.g. ConnectionResetError wrapped
            # inside ProtocolError (Sentry ANKI-HYPER-TTS-K1Y).
            if isinstance(underlying, (requests.exceptions.ConnectionError,
                                       requests.exceptions.ChunkedEncodingError)):
                raise errors.ServiceConnectionError(source_text, voice, str(e)) from e
            raise errors.UnknownServiceError(source_text, voice, str(e)) from e
        except AssertionError as e:
            # gTTS raises AssertionError("No text to send to TTS API") when the
            # tokenizer strips the input down to nothing (e.g. text like ",,,").
            raise errors.ServiceInputError(source_text, voice, str(e)) from e

