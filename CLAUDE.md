# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

### Important Development Notes

- Tests use PyQt6 and require special handling for Qt components
- The `external/` directory contains vendored dependencies to avoid user installation requirements
- Audio files are cleaned up during packaging (`package.sh` removes user_files/*.mp3, *.ogg, *.wav)
- Version is managed in `hypertts_addon/version.py`
- Sentry integration is used for error tracking in production

### Build and Package Process

The `package.sh` script handles:
1. Version bumping with bump2version
2. Git tagging and pushing
3. Creating .ankiaddon file (zip with specific structure)
4. GitHub release creation
5. File cleanup (removing meta.json, audio files, cache)

### Testing Architecture

- Uses pytest with PyQt6 API configuration
- Tests are excluded from the `external/` directory
- Coverage reporting is available
- pytest-xdist enables parallel test execution