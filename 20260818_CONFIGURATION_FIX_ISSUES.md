# Configuration Fix Issues

The backup feature can still overwrite corrupted configuration during its initial rollout, blocks legitimate removal of the final configured item, and rejects backups containing uncounted settings. It also bypasses the repository's centralized persistence invariant during restore.

## P1: Inspect `meta.json` before accepting a first install

**Location:** `hypertts_addon/__init__.py:122`

On the first launch after upgrading to this version, no backups exist yet. If an existing user's `meta.json` is malformed, Anki returns the packaged defaults, this check returns false, and `save_configuration()` overwrites the malformed file before the later startup check can detect it, permanently losing recoverable presets and API keys.

Check `meta.json` directly before writing even when no backup exists, as required by `AGENTS.md:90-92`.

## P2: Allow deliberate removal of the final configured item

**Location:** `hypertts_addon/config_backup.py:498-503`

When a user deletes their last preset or removes their last configured service/API key, the current configuration becomes `looks_empty()` while the previous backup has user data. This rejects the intentional save, sets `config_writes_blocked`, and prevents every subsequent configuration write until recovery or restart, even though the change came through a normal UI action.

## P2: Treat all user-configurable settings as restorable data

**Location:** `hypertts_addon/config_backup.py:67-75`

Configurations containing only an extension directory, disabled-service choices, or other fields such as editor selection are classified as having no user data because none of those settings are counted here. Their backup is shown as empty, the Restore button remains disabled, and `load_backup_config()` rejects it, so users cannot restore those settings despite the backup containing them.

## P2: Route restored configurations through `persist_config`

**Location:** `hypertts_addon/hypertts.py:121`

This direct write bypasses the new persistence choke point and its pre-write anomaly checks, contrary to the configuration safety invariant in `AGENTS.md:86-89`.

After unblocking the intentional restore, call `persist_config()` so restoration cannot silently bypass current or future backup and validation behavior.

## P3: Assign object names to every new backup widget

**Location:** `hypertts_addon/component_config_backup.py:39-40`

The new description label and root `layout_widget` lack stable `objectName` values, so live Anki GUI automation cannot reliably identify them.

Assign `hypertts_config_backup_*` names as required by `AGENTS.md:121-122`.
