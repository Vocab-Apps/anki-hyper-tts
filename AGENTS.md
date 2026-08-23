# AGENTS.md

This file provides guidance to AI agents when working with code in this repository.

## Project Overview

HyperTTS is an advanced text-to-speech addon for Anki, positioned as "AwesomeTTS 2.0". It allows users to add speech audio to flashcards using 20+ TTS services including cloud providers (Amazon Polly, Azure, Google, OpenAI, ElevenLabs) and local TTS engines.

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run tests in parallel
pytest -n auto

# Run with coverage
coverage run -m pytest && coverage report

# Run specific test file
pytest tests/test_component_batchdownload.py

# Show captured output during tests
pytest --show-capture=all
```

### Version Management and Release
```bash
# Bump version (major/minor/patch)
./package.sh patch "Release notes here"

# Manual version bump only
bump2version patch
```

### Development Dependencies
```bash
# Install development dependencies
pip install -r requirements.txt
```

### GitHub Issues
```bash
# List open issues
gh issue list
```

## Code Architecture

### Core Components

- **`hypertts_addon/hypertts.py`** - Main application class that orchestrates TTS operations
- **`hypertts_addon/servicemanager.py`** - Manages all TTS service integrations and voice discovery
- **`hypertts_addon/gui.py`** - Main UI integration with Anki's interface

### Service Integration Pattern

All TTS services follow a standard pattern in `hypertts_addon/services/`:
- Each service implements a common interface defined in `service.py`
- Services handle voice discovery, audio generation, and error handling
- Configuration is managed through service-specific config models

### Key Directories

- **`hypertts_addon/`** - Main addon code
- **`hypertts_addon/services/`** - TTS service implementations  
- **`external/`** - Bundled third-party dependencies (boto3, gtts, etc.)
- **`tests/`** - Comprehensive test suite with PyQt6 support
- **`user_files/`** - Directory for generated audio files

### Configuration System

The addon uses a sophisticated configuration system:
- **`config.json`** - Default configuration
- **`meta.json`** - Runtime configuration including API keys (excluded from releases)
- **`config_models.py`** - Pydantic models for type-safe configuration

Configuration safety (github issue #360, configuration loss):
- **`config_backup.py`** - rolling backups in `user_files/config_backup/` (written atomically, most
  recent 30 kept, identical configurations deduplicated), configuration statistics, and detection of
  data loss / corrupt `meta.json`, reported to Sentry as `errors.ConfigurationAnomaly`
- **`component_config_backup.py`** - the *Configuration Backups* tab of the Preferences screen, where
  a user can inspect and restore a backup
- all configuration writes go through `HyperTTS.persist_config()`, never
  `anki_utils.write_config()` directly: it takes the backup and refuses to persist a configuration
  which lost all its data *and* no longer carries the `user_uuid` of the last backup (anki hands out
  `config.json` defaults when `meta.json` cannot be parsed, and writing those back is what makes the
  loss permanent). the `user_uuid` is what distinguishes a configuration we failed to read from one
  the user emptied on purpose, e.g. by deleting their last preset or removing their API key — those
  saves must always go through
- HyperTTS never writes the configuration on startup unless a migration actually changed it, and
  `hypertts_addon/__init__.py` only writes a newly generated `user_uuid` when the backups agree that
  this really is a first install

### Important Development Notes

- Tests use PyQt6 and require special handling for Qt components
- The `external/` directory contains vendored dependencies to avoid user installation requirements
- Audio files are cleaned up during packaging (`package.sh` removes user_files/*.mp3, *.ogg, *.wav)
- Version is managed in `hypertts_addon/version.py`
- Sentry integration is used for error tracking in production

### Logging

Get a logger with `logging_utils.get_child_logger(__name__)` — never `print()`, and never a bare
`logging.getLogger()` (that logger sits outside the `hypertts` tree, propagates to Anki's root
logger, and is dropped by `sentry_utils.sentry_filter`). It is a plain `logging.Logger`, so the
whole stdlib API is available, `exception()` and `exc_info=True` included.

Inside Anki nothing is written to stdout or stderr: the `hypertts` logger has `propagate = False`
and only a `NullHandler`, because Anki turns anything appearing on stderr into a confusing error
message for the user. Records are still seen by Sentry, whose `LoggingIntegration` hooks
`logging.Logger.callHandlers` rather than installing a handler — every record becomes a breadcrumb
and **ERROR and above becomes a Sentry issue**, so use `warning` for conditions you expect to
happen. To get output locally, set `HYPER_TTS_DEBUG_LOGGING=enable` (stdout) or
`HYPER_TTS_DEBUG_LOGGING=file` with `HYPER_TTS_DEBUG_LOGFILE=<path>`.

Log records can additionally be shipped to Sentry Logs, off by default and enabled either by the
*Send detailed HyperTTS logs* preference or by the `sentry-full-reporting` PostHog feature flag
(`logging_utils.enable_sentry_remote_logging()`).

### Build and Package Process

The `package.sh` script handles:
1. Version bumping with bump2version
2. Git tagging and pushing
3. Creating .ankiaddon file (zip with specific structure)
4. GitHub release creation
5. File cleanup (removing meta.json, audio files, cache)

### GUI Development Against a Live Anki Instance

When adding or changing a HyperTTS dialog, use the `anki-gui-automation` skill
(`.claude/skills/anki-gui-automation/SKILL.md`). It launches a real Anki instance headlessly on a
throwaway profile via `scripts/gui_automation/`, injects notes with AnkiConnect, and exposes the
live Qt widget tree as text so dialogs can be inspected and driven without pixel hunting. Machine
setup is documented in `docs/AI_GUI_AUTOMATION_SETUP.md`.

The Anki source code is available locally at `/home/luc/src/anki/`.

- give every widget you create a stable `objectName` prefixed `hypertts_<screen>_`; see
  `hypertts_addon/component_remove_audio.py` for the reference implementation
- always run `scripts/gui_automation/teardown.sh` when finished
- new dialogs still need pytest-qt tests plus a `test_<name>_manual` entry in
  `scripts/openbox_menu_hypertts`

### Testing Architecture

- Uses pytest with PyQt6 API configuration
- Tests are excluded from the `external/` directory
- Coverage reporting is available
- pytest-xdist enables parallel test execution
- test for TTS services should be inside @tests/test_tts_services/ (per-service test files inheriting from base.py)
