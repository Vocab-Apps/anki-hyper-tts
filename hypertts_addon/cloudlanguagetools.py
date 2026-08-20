import sys
import os
import socket
import requests
import json
import base64
from typing import Optional

from . import errors
from . import version
from . import constants
from . import config_models
from . import voice as voice_module
from . import logging_utils
from . import config_models
logger = logging_utils.get_child_logger(__name__)

try:
    from urllib3.exceptions import ReadTimeoutError as _Urllib3ReadTimeoutError
except Exception:  # pragma: no cover - urllib3 is a hard dep of requests
    _Urllib3ReadTimeoutError = None


def _is_wrapped_read_timeout(exc):
    """Return True if exc is a read timeout that requests re-raised as a plain
    ConnectionError (not a Timeout subclass).

    When ``Session.post`` is called with ``stream=False`` (the default),
    requests reads the response body during the call. A urllib3
    ReadTimeoutError raised mid-read is wrapped in
    ``requests.exceptions.ConnectionError`` rather than
    ``requests.exceptions.Timeout``, so the ``except requests.exceptions.Timeout``
    handler misses it and the error is mis-tagged as ServiceConnectionError
    (Sentry ANKI-HYPER-TTS-KC2). The cause chain is linked via __context__
    (implicit "during handling"), not __cause__, so walk both.
    """
    seen = set()
    cur = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, socket.timeout):
            return True
        if _Urllib3ReadTimeoutError is not None and isinstance(cur, _Urllib3ReadTimeoutError):
            return True
        cur = cur.__cause__ or cur.__context__
    # Fallback: urllib3 ReadTimeoutError's canonical message.
    return 'Read timed out' in str(exc)

if hasattr(sys, '_sentry_crash_reporting'):
    import sentry_sdk
    def _start_span(op, name=None):
        return sentry_sdk.start_span(op=op, name=name)
else:
    import contextlib
    @contextlib.contextmanager
    def _start_span(op, name=None):
        yield None

class CloudLanguageTools():
    def __init__(self):
        self.vocabai_api_base_url = os.environ.get('ANKI_LANGUAGE_TOOLS_VOCABAI_BASE_URL', constants.VOCABAI_API_BASE_URL)
        self.disable_ssl_verification = False
        self.session = requests.Session()
        logger.info(f'using VocabAi API base URL: {self.vocabai_api_base_url}')

    def configure(self, config: config_models.Configuration, disable_ssl_verification: bool = False):
        self.config = config
        self.disable_ssl_verification = disable_ssl_verification
        if self.disable_ssl_verification:
            logger.warning('SSL verification is disabled for cloud language tools connections')

    def get_request_headers(self):
        return {
            'Authorization': f'Api-Key {self.config.hypertts_pro_api_key}',
        }

    def get_trial_request_headers(self):
        return {
            'User-Agent': f'anki-hyper-tts/{version.ANKI_HYPER_TTS_VERSION}',
            'X-Vocab-Addon-ID': self.config.user_uuid
        }

    def get_vocabai_url(self, path):
        if self.config.vocabai_api_url_override != None:
            base_url = self.config.vocabai_api_url_override
        else:
            base_url = self.vocabai_api_base_url
        return base_url + f'/languagetools-api/v5/{path}'

    def get_verify_ssl(self):
        """Returns the SSL verification setting for requests. Returns True (verify SSL) by default."""
        return not self.disable_ssl_verification

    # Raises only subclasses of:
    #   PermanentError  – non-retryable (400, 403, 404)
    #   TransientError  – retryable (502, 503, 504, timeout, unknown)
    def get_tts_audio(self, source_text, voice, options, audio_request_context):
        return self._get_tts_audio_vocabai(source_text, voice, options, audio_request_context)

    def _get_tts_audio_vocabai(self, source_text, voice, options, audio_request_context):
        # API v5
        full_url = self.get_vocabai_url('audio')
        data = {
            'text': source_text,
            'service': voice.service,
            'request_mode': audio_request_context.get_request_mode().name,
            'client': constants.CLIENT_NAME,
            'client_version': version.ANKI_HYPER_TTS_VERSION,
            'client_uuid': self.config.user_uuid,
            'batch_uuid': audio_request_context.get_batch_uuid_str(),
            'language_code': voice_module.get_audio_language_for_voice(voice).lang.name,
            'voice_key': voice.voice_key,
            'options': options,
            'retry_count': audio_request_context.retry_count,
            'retry_max': audio_request_context.retry_max,
        }
        logger.info(f'_get_tts_audio_vocabai: request url: {full_url}, data: {data}')
        headers = self.get_request_headers()
        logger.debug(f'_get_tts_audio_vocabai: headers: {headers} data: {data}')

        try:
            with _start_span(op="http.request.wrapped", name=f"POST {full_url}"):
                response = self.session.post(full_url, json=data, headers=headers,
                    timeout=constants.RequestTimeout, verify=self.get_verify_ssl())
            logger.info(f'_get_tts_audio_vocabai: response status_code: {response.status_code}')

            if response.status_code == 200:
                # success
                return response.content

            if response.status_code == 404:
                # not found (for example on Forvo)
                raise errors.AudioNotFoundError(source_text, voice)

            # try to extract response JSON; fall back to raw content
            try:
                response_data = response.json()
            except (ValueError, Exception):
                response_data = None

            if response.status_code == 400:
                if response_data is not None:
                    if 'error' in response_data:
                        raise errors.PermanentError(source_text, voice, response_data['error'])
                    raise errors.PermanentError(source_text, voice, str(response_data))
                raise errors.PermanentError(source_text, voice, str(response.content))
            elif response.status_code == 403:
                # permission issue
                detail = response_data.get('detail', 'Forbidden') if response_data else 'Forbidden'
                raise errors.ServicePermissionError(source_text, voice, detail)
            elif response.status_code == 502:
                # upstream gateway error (e.g. Forvo returned a bad response)
                error_msg = response_data.get('error', 'bad gateway') if response_data else 'bad gateway'
                raise errors.ServiceGatewayError(source_text, voice, error_msg)
            elif response.status_code == 503:
                # transient error with retry-after in seconds
                if response_data:
                    retry_after = response_data.get('retry_after', 30)
                    error_msg = response_data.get('error', 'rate limited')
                else:
                    retry_after = 30
                    error_msg = 'rate limited'
                raise errors.RateLimitRetryAfterError(source_text, voice, error_msg, retry_after)
            elif response.status_code == 504:
                # transient error without specific retry-after
                error_msg = response_data.get('error', 'temporary failure') if response_data else 'temporary failure'
                raise errors.TransientError(source_text, voice, error_msg)

            # default: log full details and raise
            error_message = f"Status code: {response.status_code} ({response.content})"
            raise errors.UnknownServiceError(source_text, voice, error_message)

        except errors.HyperTTSError:
            # we need to let the exceptions created by parsing the payload through,
            # since they have the correct error type and message
            raise
        except requests.exceptions.Timeout:
            raise errors.ServiceTimeoutError(source_text, voice, 'HTTP request timed out')
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError) as e:
            # ChunkedEncodingError is raised when the connection drops mid-response
            # (e.g. RST while streaming the body). It is a sibling of ConnectionError
            # in requests, not a subclass, so it must be listed explicitly — otherwise
            # it falls through to the generic handler and gets mis-tagged as
            # UnknownServiceError (Sentry ANKI-HYPER-TTS-JM3).
            # A read timeout during the body read (stream=False default) is wrapped by
            # requests in ConnectionError, not Timeout — reclassify it so it lands in
            # the ServiceTimeoutError Sentry group instead of ServiceConnectionError
            # (Sentry ANKI-HYPER-TTS-KC2).
            if _is_wrapped_read_timeout(e):
                raise errors.ServiceTimeoutError(source_text, voice, str(e)) from e
            raise errors.ServiceConnectionError(source_text, voice, str(e))
        except Exception as e:
            # eventually we should not have any exceptions coming through here
            # for now, classify them as unknown service errors, which is a TransientError
            raise errors.UnknownServiceError(source_text, voice, str(e))

    def account_info(self, api_key):
        vocabai_url = self.get_vocabai_url('account')
        logger.info(f'account_info: request url: {vocabai_url}, data: None')
        response = self.session.get(vocabai_url, headers={
                'Authorization': f'Api-Key {api_key}',
                'User-Agent': f'anki-hyper-tts/{version.ANKI_HYPER_TTS_VERSION}'},
            verify=self.get_verify_ssl()
        )
        logger.info(f'account_info: response status_code: {response.status_code}')
        if response.status_code == 200:
            logger.debug(f'vocabai API result: {response.json()}')
            # API key is valid on vocab API
            return config_models.HyperTTSProAccountConfig(
                api_key=api_key,
                api_key_valid=True,
                use_vocabai_api=True,
                account_info=response.json()
            )

        # default case, API key is not valid
        return config_models.HyperTTSProAccountConfig(
            api_key=api_key,
            api_key_valid=False,
            api_key_error='API key not found')

    def account_email_no_except(self, api_key) -> Optional[str]:
        try:
            url = self.get_vocabai_url('account')
            response = self.session.get(
                url,
                headers={
                    'Authorization': f'Api-Key {api_key}',
                    'User-Agent': f'anki-hyper-tts/{version.ANKI_HYPER_TTS_VERSION}',
                },
                timeout=constants.RequestTimeoutShort,
                verify=self.get_verify_ssl(),
            )
            if response.status_code != 200:
                return None
            return response.json().get('email')
        except Exception:
            return None


    def build_trial_key_request_data(self, email, password, client_uuid):
        namespace = {}
        exec(base64.b64decode(constants.REQUEST_TRIAL_PAYLOAD).decode('utf-8'), namespace)
        data = namespace['build_trial_request_payload'](email, client_uuid)
        data['email'] = email
        data['password'] = password
        return data

    def check_email_verification_status(self, email) -> bool:
        url = self.get_vocabai_url('check_email_verification')
        logger.info(f'check_email_verification_status: request url: {url}, data: None')

        response = self.session.get(url,
                               headers=self.get_request_headers(),
                               verify=self.get_verify_ssl())
        logger.info(f'check_email_verification_status: response status_code: {response.status_code}')

        if response.status_code != 200:
            error_message = f"Status code: {response.status_code} ({response.content})"
            raise errors.RequestError(email, None, error_message)
        
        data = json.loads(response.content)
        return data['email_verified']

    def request_trial_key(self, email, password, client_uuid) -> config_models.TrialRequestReponse:
        url = self.get_vocabai_url('register_trial')
        data = self.build_trial_key_request_data(email, password, client_uuid)
        logger.info(f'request_trial_key: request url: {url}, data: {data}')
        response = self.session.post(url,
                                 json=data,
                                 headers=self.get_trial_request_headers(),
                                 verify=self.get_verify_ssl())
        logger.info(f'request_trial_key: response status_code: {response.status_code}')
        data = json.loads(response.content)

        if response.status_code == 201:
            # trial key was successfully created
            return config_models.TrialRequestReponse(
                success=True,
                api_key=data['api_key']
            )
        else:
            error_message = '<b>error:</b> ' + ', '.join([f"{key}: {value}" for key, value in data.items()])
            return config_models.TrialRequestReponse(
                success=False,
                error=error_message
            )
