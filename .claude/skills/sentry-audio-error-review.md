---
description: "Review unresolved Sentry audio-request issues from the last 24 hours and report any whose exception_type looks mis-categorized against hypertts_addon/errors.py"
user_invocable: true
---

# Sentry Audio-Error Categorization Review

Pull every unresolved HyperTTS audio-request issue from the last 24 hours, judge whether each
issue's `exception_type` tag matches the actual error evidence, and report any that look
mis-categorized so the service code can be fixed.

Every audio-request exception is captured at `hypertts_addon/servicemanager.py:232-246` with the
tag `is_audio_request_exception: True`. The exception class name is captured in the `exception_type`
tag and the retryable flag in `error_retryable`. When a service maps an HTTP response or network
failure to the wrong subclass of `ServiceRequestError`, retry logic and triage signal both
degrade — that is what this skill catches.

## Sentry coordinates (hard-coded)

- Organization slug: `language-tools`
- Project ID: `6170140`
- Sentry filter: `is:unresolved is_audio_request_exception:True`, last 24h
- Canonical issue URL form: `https://language-tools.sentry.io/issues/<shortId>/`

## Step 1 — Pull the issue list

Call `mcp__sentry__search_issues` with:

- `organizationSlug='language-tools'`
- `projectSlugOrId='6170140'`
- `naturalLanguageQuery="unresolved issues with tag is_audio_request_exception:True from the last 24 hours"`
- `limit=100`

Record each issue's shortId, title, and Sentry URL. If zero issues are returned, report
"No unresolved audio-request issues in the last 24 hours" and stop.

## Step 2 — Gather evidence for each issue

For each issue, call `mcp__sentry__get_sentry_resource` with the issue URL. From the latest
event extract:

- `exception_type` tag — the current categorization
- `error_retryable` tag — the current retryable flag
- `audio_service` tag — which service raised it
- The exception class name and message in the stack trace
- Any HTTP status code, underlying exception type, or low-level error string referenced in
  the message (e.g. `502 Bad Gateway`, `requests.exceptions.ConnectionError`,
  `Connection refused`, `ReadTimeout`, `Name or service not known`)

If an issue's tags or event payload don't contain enough evidence to judge the categorization,
note it as "insufficient evidence" rather than flagging it.

## Step 3 — Apply the categorization rules

Use this table — derived from `hypertts_addon/errors.py` and the mapping logic in
`hypertts_addon/cloudlanguagetools.py` and `hypertts_addon/servicemanager.py` — to judge
whether `exception_type` matches the evidence:

| Evidence in event | Correct exception | Retryable |
|---|---|---|
| HTTP 401 or 403 | `ServicePermissionError` | False |
| HTTP 404 (audio not found for that text/voice) | `AudioNotFoundError` | False |
| All priority-mode voices exhausted | `AudioNotFoundAnyVoiceError` | False |
| Unsupported input (e.g. requested audio format not available) | `ServiceInputError` | False |
| HTTP 429 with `Retry-After` | `RateLimitRetryAfterError` | True |
| HTTP 502 / 503 / 504 (no Retry-After) | `ServiceGatewayError` | True |
| `requests.exceptions.Timeout` / "timed out" / "ReadTimeout" | `ServiceTimeoutError` | True |
| `requests.exceptions.ConnectionError` / "Connection refused" / "Name or service not known" / "Network is unreachable" | `ServiceConnectionError` | True |
| Anything else / no clear classifier | `UnknownServiceError` | True |

Mis-categorization heuristic — flag an issue when **any** of these hold:

- The evidence clearly matches a specific row above but `exception_type` is the catch-all
  `UnknownServiceError` (or the legacy `RequestError`). A more specific class would have
  improved retry logic and grouping.
- A permanent error (rows where Retryable=False) is currently tagged with a transient class,
  or vice versa — compare the table's Retryable column against the `error_retryable` tag.
- The evidence points to a different specific row than `exception_type` claims (e.g. tagged
  `ServiceTimeoutError` but the trace shows a 502 response).

Do **not** flag an issue when the categorization is correct or when there is insufficient
evidence in the event to judge.

## Step 4 — Report

For each mis-categorized issue, print:

- **URL:** `https://language-tools.sentry.io/issues/<shortId>/`
- **Service:** value of `audio_service` tag
- **Currently tagged as:** `<exception_type>` (`error_retryable=<bool>`)
- **Evidence:** 1–2 lines quoted from the stack trace or message
- **Suggested category:** `<class>` — and where in the service code the mapping should be
  added or fixed (look at the `audio_service` tag to find the right `services/service_<x>.py`,
  or `cloudlanguagetools.py` for CLT-routed services)

End the report with a one-line summary: `Reviewed N issues, M look mis-categorized.`
If `M == 0`, say so explicitly — don't stay silent.

## Reference: where the rules live in code

- `hypertts_addon/errors.py` — full exception hierarchy
- `hypertts_addon/servicemanager.py:232-298` — Sentry tagging plus the
  `requests.exceptions.Timeout` / `ConnectionError` / generic `Exception` fallback handler
  that maps to `ServiceTimeoutError` / `ServiceConnectionError` / `UnknownServiceError`
- `hypertts_addon/cloudlanguagetools.py:109-200` — the most thorough HTTP-status-to-error
  mapping in the codebase; use it as a model for what good categorization looks like
