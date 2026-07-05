# Forvo Chinese dialect voices collapse to a single API request (Northeastern Mandarin ↔ Minnan confusion)

## Summary

The Forvo service advertises a large set of "Chinese dialect" voices (Northeastern
Mandarin, Minnan, Wu, Henan, Shaanxi, Sichuan, etc.) in the voice list, but every one
of these voices shares the **same** `voice_key`. At audio-generation time the Forvo
service builds its API request from only the `voice_key`, so all dialect voices
produce the **identical** Forvo API call and therefore return the same audio. The
dialect distinction exists only in listing metadata (`audio_languages`) and is never
transmitted to Forvo. As a result, selecting "Chinese (Northeastern Mandarin,
Simplified)" can (and does) return Minnan audio, and vice versa.

## Symptom

- A user picks the Forvo voice labeled **Chinese (Northeastern Mandarin, Simplified)**
  (`AudioLanguage.zh_CN_liaoning`).
- Forvo returns whichever `zh-CHN` recording happens to be top-rated at the moment
  (typically Standard Mandarin, but the same Forvo bucket also contains Min Nan / Wu
  / Hakka recordings that contributors tagged under `zh`).
- Selecting **Chinese Minnan** (`AudioLanguage.nan_CN`) instead produces the same
  request and the same audio.
- All dialect-level Forvo Chinese voices are functionally indistinguishable.

## Root cause

### 1. Voice list: identical `voice_key`, distinct `audio_languages`

In `hypertts_addon/services/voicelist.py`, the Forvo block (~420 entries starting
around line 16312) contains one `TtsVoice_v3` per (gender × dialect) combination. For
mainland Chinese dialects the `voice_key` is the same for every entry:

```python
voice_key={'language_code': 'zh', 'country_code': 'CHN', 'gender': 'm'}
```

Only the `audio_languages` field differs:

| Line      | name     | voice_key                                                        | audio_languages            |
|-----------|----------|------------------------------------------------------------------|----------------------------|
| 21304     | zh-CHN   | `{'language_code':'zh','country_code':'CHN','gender':'m'}`        | `nan_CN` (Minnan)          |
| 21317     | zh-CHN   | `{'language_code':'zh','country_code':'CHN','gender':'m'}`        | `zh_CN` (Mandarin)         |
| 21330     | zh-CHN   | `{'language_code':'zh','country_code':'CHN','gender':'m'}`        | `wuu_CN` (Wu)              |
| 21343     | zh-CHN   | `{'language_code':'zh','country_code':'CHN','gender':'m'}`        | `zh_CN_henan`              |
| …         | zh-CHN   | `{'language_code':'zh','country_code':'CHN','gender':'m'}`        | `zh_CN_liaoning`           |
| …         | zh-CHN   | `{'language_code':'zh','country_code':'CHN','gender':'m'}`        | `zh_CN_shaanxi`            |
| …         | zh-CHN   | `{'language_code':'zh','country_code':'CHN','gender':'m'}`        | `zh_CN_shandong`           |
| …         | zh-CHN   | `{'language_code':'zh','country_code':'CHN','gender':'m'}`        | `zh_CN_sichuan`            |
| …         | zh-CHN   | `{'language_code':'zh','country_code':'CHN','gender':'m'}`        | `zh_CN_guangxi`            |
| …         | zh-CHN   | `{'language_code':'zh','country_code':'CHN','gender':'m'}`        | `zh_CN_gansu`              |
| …         | zh-CHN   | `{'language_code':'zh','country_code':'CHN','gender':'m'}`        | `zh_CN_anhui`              |
| …         | zh-CHN   | `{'language_code':'zh','country_code':'CHN','gender':'m'}`        | `zh_CN_hunan`              |

(The same set is duplicated for `gender='f'` and for the gender-omitted "Any"
variant, so the full set of affected entries is ~36.)

By contrast, Cantonese (`yue`) voices have a **distinct** `language_code` (`yue`) and
so are correctly separable:

| name     | voice_key                                                          | audio_languages |
|----------|--------------------------------------------------------------------|------------------|
| yue-CHN  | `{'language_code':'yue','country_code':'CHN','gender':'m'}`         | `yue_CN`         |
| yue-HKG  | `{'language_code':'yue','country_code':'HKG','gender':'m'}`         | `zh_HK`          |

### 2. Service: `voice_key` is the only thing sent to Forvo

`hypertts_addon/services/service_forvo.py:57-91` constructs the Forvo URL from
`voice_key` only:

```python
language = voice.voice_key['language_code']            # 'zh'

sex_param = ''
if 'gender' in voice.voice_key:
    sex_param = f"/sex/{voice.voice_key['gender']}"    # '/sex/m'

country_code = ''
if voice.voice_key['country_code'] != self.COUNTRY_ANY:
    country_code = f"/country/{voice.voice_key['country_code']}"  # '/country/CHN'

# ...
url = (f'{api_url}/key/{api_key}/format/json/action/word-pronunciations/'
       f'word/{encoded_text}/language/{language}{sex_param}{username_param}'
       f'/order/rate-desc/limit/1{country_code}')
```

For every `zh-CHN` dialect voice this produces:

```
.../word-pronunciations/word/<text>/language/zh/sex/m/order/rate-desc/limit/1/country/CHN
```

The dialect / sub-language (`zh_CN_liaoning`, `nan_CN`, `wuu_CN`, …) lives only in
`audio_languages`, which `get_tts_audio` never reads. Forvo's API itself has no
sub-language/dialect parameter — for it, `zh` is a single bucket that mixes Mandarin,
Min Nan, Wu, Hakka, etc. There is therefore no way for the current integration to
honour the dialect choice.

## Affected voices

All Forvo voices with `voice_key={'language_code':'zh','country_code':'CHN',...}` whose
`audio_languages` is anything other than `zh_CN` are mis-advertised:

- `nan_CN` — Chinese Minnan
- `wuu_CN` — Chinese Wu
- `zh_CN_henan` — Chinese (Zhongyuan Mandarin Henan)
- `zh_CN_liaoning` — Chinese (Northeastern Mandarin)  ← reported confusion
- `zh_CN_shaanxi` — Chinese (Zhongyuan Mandarin Shaanxi)
- `zh_CN_shandong` — Chinese (Jilu Mandarin)
- `zh_CN_sichuan` — Chinese (Southwestern Mandarin)
- `zh_CN_guangxi` — Chinese (Guangxi Accent Mandarin)
- `zh_CN_gansu` — Chinese (Lanyin Mandarin Gansu)
- `zh_CN_anhui` — Chinese (Jianghuai Mandarin Anhui)
- `zh_CN_hunan` — Chinese (Hunan Accent Mandarin)

For each of these, both `gender='m'` and `gender='f'` variants exist, and a
gender-omitted "Any" variant also exists.

## Impact

- **User-facing**: every dialect-level Forvo Chinese voice is non-functional as
  advertised. The reported case — "Northeastern Mandarin" returning Minnan audio —
  is the expected failure mode, not an edge case.
- **Trust**: the voice list suggests a level of dialect granularity that the Forvo
  API cannot deliver, which undermines confidence in the addon's Chinese support.
- **Discoverability**: because all `zh-CHN` voices share the name `zh-CHN`, the UI
  presents near-duplicate entries that differ only in their displayed language
  label, making the picker confusing.

## Reproduction

1. Configure Forvo with a working API key (free tier is enough).
2. In the HyperTTS voice picker, select the Forvo voice labeled
   **Chinese (Northeastern Mandarin, Simplified)**.
3. Generate audio for a Mandarin word, e.g. 你好.
4. Repeat with the Forvo voice labeled **Chinese Minnan**, using a word that
   differs between Mandarin and Min Nan (e.g. a word with the Minnan word list).
5. Observe that the URLs issued (and the returned audio) are identical for both
   selections — `language/zh/country/CHN`, top-rated, `limit/1`.

(Same result for any pair of `zh-CHN` dialect voices.)

## Proposed fixes

Three options, in increasing order of effort / capability:

### Option 1 — Collapse the dialect-level Forvo Chinese voices (recommended, simplest)

Remove all `zh-CHN` Forvo entries whose `audio_languages` is a dialect other than
`zh_CN`. Keep only:

- `zh-CHN` → `zh_CN`
- `zh-TWN` → `zh_TW` (if present)
- `yue-CHN` → `yue_CN`
- `yue-HKG` → `zh_HK`

This is the most honest representation of what the Forvo API can actually
distinguish (by `language_code` and `country_code`). It removes ~33 misleading entries
and makes the picker less cluttered. No code change in `service_forvo.py` is needed.

Tradeoff: users lose the (illusory) dialect choice. This is the correct outcome —
those choices never worked.

### Option 2 — Post-filter Forvo results by dialect metadata

If Forvo's corporate API (`CONFIG_API_URL_CORPORATE`) returns per-item metadata that
identifies the dialect/region (e.g. `country`, `city`, or a dialect tag), then:

1. Call Forvo **without** `limit/1` (or with a higher limit).
2. Inspect the returned `items` for dialect signals.
3. Select the first item whose dialect matches the requested `audio_languages`.

This requires verifying what the corporate endpoint actually returns. If the items
only carry `country` (which is `CHN` for all these voices), this option cannot work
and Option 1 is mandatory. The free endpoint almost certainly does not expose
dialect info beyond `language/zh`.

Tradeoff: keeps the dialect UI but only if Forvo exposes enough metadata; otherwise
falls back to Option 1.

### Option 3 — Use Forvo's per-user targeting

The code in `service_forvo.py:80-83` shows a commented-out `username_param` for a
"preferred user" feature. If specific Forvo contributors are known to record in a
given dialect, each dialect voice could pin a `preferred_user` in its `voice_key`.
This would route requests to a known-good speaker per dialect.

Tradeoff: requires curating a contributor → dialect mapping and maintaining it as
contributors come and go. Fragile and not scalable.

### Recommendation

Go with **Option 1**. It accurately reflects the Forvo API's actual granularity,
removes misleading UI entries, and requires no risky behaviour changes in
`service_forvo.py`. If Option 2 turns out to be feasible after inspecting corporate
API responses, it can be layered on top later by re-adding dialect voices with
post-filtering.

## Files to investigate / modify

- `hypertts_addon/services/voicelist.py` — the Forvo block (lines ~16312–21763),
  specifically the `zh-CHN` entries around lines 21304–21519 (and their `gender='f'`
  / gender-omitted duplicates).
- `hypertts_addon/services/service_forvo.py` — `get_tts_audio` (lines 57–91),
  particularly the URL construction at lines 69–91 that ignores `audio_languages`.
- `hypertts_addon/languages.py` — definitions of `AudioLanguage.zh_CN_*` (lines
  466–473), `nan_CN`, `wuu_CN`, `yue_CN`. These definitions themselves are fine; the
  issue is purely how Forvo voices are wired to them.
- `tests/test_tts_services/test_forvo.py` — existing Forvo tests; no test currently
  covers the Chinese dialect voices, which is why this slipped through. A regression
  test should assert that two distinct `audio_languages` voices for the same service
  produce audibly different requests/responses (or that the duplicate voices no
  longer exist after the fix).

## Notes

- The fact that all `zh-CHN` voices share the display name `zh-CHN` is itself a minor
  UI bug: even before the audio bug, the picker shows several identical "zh-CHN"
  rows whose only distinguishing feature is the language label.
- Forvo is a `constants.ServiceType.dictionary` service (`service_forvo.py:36`), so it
  returns real human recordings, not synthesised speech; the dialect mismatch is
  therefore a content-correctness problem, not just an accent difference.
