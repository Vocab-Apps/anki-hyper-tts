---
description: "Guide for writing a new HyperTTS TTS or dictionary service"
user_invocable: true
---

# How to Write a HyperTTS Service

You are helping the user create a new TTS or dictionary service for the HyperTTS Anki addon. Use the reference below to guide implementation.

## Key Source Files

| File | Purpose |
|------|---------|
| `hypertts_addon/service.py` | `ServiceBase` abstract class all services extend |
| `hypertts_addon/voice.py` | `TtsVoice_v3` dataclass representing a voice |
| `hypertts_addon/languages.py` | `Language` and `AudioLanguage` enums |
| `hypertts_addon/constants.py` | `Gender`, `ServiceType`, `ServiceFee` enums |
| `hypertts_addon/errors.py` | `RequestError`, `AudioNotFoundError` exceptions |
| `hypertts_addon/options.py` | `AudioFormat` enum, `AUDIO_FORMAT_PARAMETER` constant |

## Service Discovery

Services are auto-discovered by `ServiceManager`. To be discovered:
1. Place the file in `hypertts_addon/services/`
2. Name it `service_<yourservice>.py`
3. Subclass `ServiceBase` — the manager finds all `ServiceBase` subclasses automatically

## ServiceBase Required Interface

Every service must subclass `ServiceBase` and implement:

```python
from hypertts_addon import service
from hypertts_addon import constants
from hypertts_addon import voice
from hypertts_addon import languages

class MyService(service.ServiceBase):
    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        # constants.ServiceType.tts       — generates audio for any text
        # constants.ServiceType.dictionary — looks up recordings of individual words
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        # constants.ServiceFee.free or constants.ServiceFee.paid
        return constants.ServiceFee.paid

    def voice_list(self) -> list[voice.TtsVoice_v3]:
        # Return the list of available voices
        ...

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, options) -> bytes:
        # Generate or fetch audio, return raw bytes (typically MP3)
        ...
```

## Optional Methods

```python
def configuration_options(self):
    """Declare config fields the user must fill in (API keys, regions, etc.)."""
    return {
        'api_key': str,           # text input
        'throttle_seconds': float, # numeric input
        'region': ['us-east-1', 'eu-west-1'],  # dropdown list
    }

def configure(self, config):
    """Called with the user's config dict. Validate/store values here."""
    self._config = config
    self.api_key = self.get_configuration_value_mandatory('api_key')

def enabled_by_default(self):
    """Return True if service needs no config to work (e.g. free web services)."""
    return False

def cloudlanguagetools_enabled(self):
    """Return True if this service is also available through the Cloud Language Tools proxy."""
    return False
```

### Configuration Helpers (inherited from ServiceBase)

```python
# Raises MissingServiceConfiguration if key is missing or empty string
value = self.get_configuration_value_mandatory('api_key')

# Returns default_value if key is missing
value = self.get_configuration_value_optional('throttle_seconds', 0)
```

## Building the Voice List

Each voice is a `TtsVoice_v3` instance. Do **not** use `basic_voice_list()` — build voices directly.

### TtsVoice_v3 Fields

```python
@dataclasses.dataclass
class TtsVoice_v3:
    name: str                                       # Display name shown to user
    voice_key: Dict[str, Any]                       # Service-specific identifier (dict or str)
    options: Dict[str, Dict[str, Any]]              # Adjustable parameters
    service: str                                    # Service name string (use self.name)
    gender: constants.Gender                        # Gender.Male, Gender.Female, or Gender.Any
    audio_languages: List[languages.AudioLanguage]  # Supported AudioLanguage values
    service_fee: constants.ServiceFee               # ServiceFee.free or ServiceFee.paid
```

### Using build_voice_v3 Helper

For single-language voices:

```python
from hypertts_addon import voice

voices.append(voice.build_voice_v3(
    name='English Voice',
    gender=constants.Gender.Female,
    language=languages.AudioLanguage.en_US,
    service=self,
    voice_key={'name': 'my-voice-id'},
    options={}
))
```

### Constructing TtsVoice_v3 Directly

For more control (e.g. multilingual voices):

```python
voice.TtsVoice_v3(
    name='UK English',
    gender=constants.Gender.Female,
    audio_languages=[languages.AudioLanguage.en_GB],
    service=self.name,
    voice_key='uk',
    options={},
    service_fee=self.service_fee
)
```

## Voice Options

Options let users adjust parameters like speed, pitch, or audio format:

```python
options = {
    'speed': {
        'type': 'number',     # float slider
        'min': 0.25, 'max': 4.0, 'default': 1.0
    },
    'pitch': {
        'type': 'number_int', # integer slider
        'min': -20, 'max': 20, 'default': 0
    },
    'model': {
        'type': 'list',       # dropdown
        'values': ['standard', 'hd'], 'default': 'standard'
    },
    'instructions': {
        'type': 'text',       # free text input
        'default': ''
    }
}
```

### Audio Format Option

```python
from hypertts_addon import options

format_option = {
    options.AUDIO_FORMAT_PARAMETER: {
        'type': 'list',
        'values': [e.name for e in options.AudioFormat],
        'default': 'mp3'
    }
}
```

Read it in `get_tts_audio`:

```python
audio_format_str = voice_options.get(options.AUDIO_FORMAT_PARAMETER, options.AudioFormat.mp3.name)
audio_format = options.AudioFormat[audio_format_str]
```

## Generating Audio (get_tts_audio)

```python
def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, voice_options) -> bytes:
```

- `source_text` — the text to speak
- `voice` — the `TtsVoice_v3` selected by the user; use `voice.voice_key` to identify the voice
- `voice_options` — dict of user-selected option values; fall back to defaults from `voice.options`
- **Return** raw audio bytes (MP3 by default)

### Reading Options with Defaults

```python
speed = voice_options.get('speed', voice.options['speed']['default'])
```

### Error Handling

Services should only raise exceptions derived from `PermanentError` (non-retryable) or `TransientError` (retryable). The `ServiceManager._get_tts_audio_service` method wraps service calls and automatically catches:
- `requests.exceptions.Timeout` → converted to `ServiceTimeoutError` (transient)
- Any other unhandled exception → converted to `UnknownServiceError` (transient)

So you do **not** need to catch HTTP timeouts or unknown exceptions yourself. Only raise explicit errors when you can classify them:

```python
from hypertts_addon import errors

# --- PermanentError (non-retryable) ---

# Dictionary services — word not found in dictionary
raise errors.AudioNotFoundError(source_text, voice)

# Authentication/permission failures (e.g. invalid API key, 401/403)
raise errors.ServicePermissionError(source_text, voice, 'Invalid API key')

# Any other non-retryable error
raise errors.PermanentError(source_text, voice, 'Unsupported voice format')

# --- TransientError (retryable) ---

# Rate limiting with a Retry-After header
raise errors.RateLimitRetryAfterError(source_text, voice, 'Rate limited', retry_after=30)

# Any other retryable error
raise errors.TransientError(source_text, voice, 'Server returned 503')
```

The full hierarchy:
```
ServiceRequestError(source_text, voice, error_message)
├── PermanentError          (retryable = False)
│   ├── AudioNotFoundError  — word not found (dictionary services)
│   └── ServicePermissionError — auth/permission failures
└── TransientError          (retryable = True)
    ├── ServiceTimeoutError — auto-caught from requests.exceptions.Timeout
    ├── UnknownServiceError — auto-caught from unhandled exceptions
    └── RateLimitRetryAfterError(retry_after=N) — rate limiting
```

## Complete Example: TTS Service with API Key

```python
import requests
from typing import List

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import logging_utils

logger = logging_utils.get_child_logger(__name__)


class ExampleTTS(service.ServiceBase):
    CONFIG_API_KEY = 'api_key'

    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.paid

    def configuration_options(self):
        return {self.CONFIG_API_KEY: str}

    def voice_list(self) -> List[voice.TtsVoice_v3]:
        voice_options = {
            'speed': {'type': 'number', 'min': 0.5, 'max': 2.0, 'default': 1.0}
        }
        return [
            voice.TtsVoice_v3(
                name='Alice',
                gender=constants.Gender.Female,
                audio_languages=[languages.AudioLanguage.en_US],
                service=self.name,
                voice_key={'name': 'alice'},
                options=voice_options,
                service_fee=self.service_fee
            ),
            voice.TtsVoice_v3(
                name='Bob',
                gender=constants.Gender.Male,
                audio_languages=[languages.AudioLanguage.en_US, languages.AudioLanguage.en_GB],
                service=self.name,
                voice_key={'name': 'bob'},
                options=voice_options,
                service_fee=self.service_fee
            ),
        ]

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, voice_options):
        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)
        speed = voice_options.get('speed', voice.options['speed']['default'])

        response = requests.post(
            'https://api.example.com/v1/tts',
            json={'text': source_text, 'voice': voice.voice_key['name'], 'speed': speed},
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=30,
        )
        if response.status_code == 401:
            raise errors.ServicePermissionError(source_text, voice, 'Invalid API key')
        if response.status_code != 200:
            raise errors.PermanentError(source_text, voice, f'HTTP {response.status_code}: {response.text}')
        return response.content
```

## Complete Example: Dictionary Service (Web Scraping)

```python
import requests
import bs4

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import logging_utils

logger = logging_utils.get_child_logger(__name__)


class ExampleDictionary(service.ServiceBase):

    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.dictionary

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.free

    def enabled_by_default(self):
        return True

    def voice_list(self):
        return [
            voice.TtsVoice_v3(
                name='US English',
                gender=constants.Gender.Any,
                audio_languages=[languages.AudioLanguage.en_US],
                service=self.name,
                voice_key='us',
                options={},
                service_fee=self.service_fee
            ),
        ]

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, voice_options):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'}
        response = requests.get(f'https://dictionary.example.com/{source_text}', headers=headers)
        soup = bs4.BeautifulSoup(response.content, 'html.parser')

        audio_tag = soup.find('source', {'type': 'audio/mpeg'})
        if audio_tag and audio_tag.get('src'):
            audio_response = requests.get(audio_tag['src'], headers=headers)
            return audio_response.content

        raise errors.AudioNotFoundError(source_text, voice)
```

## Example Services to Study

Read these existing implementations for reference patterns:
- `hypertts_addon/services/service_cambridge.py` — Simple dictionary service (web scraping, no config)
- `hypertts_addon/services/service_googletranslate.py` — Simple free TTS service
- `hypertts_addon/services/service_openai.py` — Paid API service with options

## Testing

Tests for TTS services go in `tests/test_tts_services/` and inherit from `tests/test_tts_services/base.py`. Run tests with:

```bash
pytest tests/test_tts_services/test_<yourservice>.py
```
