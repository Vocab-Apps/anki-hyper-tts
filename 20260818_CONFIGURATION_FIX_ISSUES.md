# Configuration Fix Issues

## P2: Allow deliberate removal of the final configured item

**Location:** `hypertts_addon/config_backup.py:498-503`

When a user deletes their last preset or removes their last configured service/API key, the current configuration becomes `looks_empty()` while the previous backup has user data. This rejects the intentional save, sets `config_writes_blocked`, and prevents every subsequent configuration write until recovery or restart, even though the change came through a normal UI action.

I have tested the following:
- removing the last preset works, the configuration is persisted.
- however, removing the HyperTTS Pro API key doesn't work. This should be allowed.

Implement a fix, and user `anki-gui-automation` skill to verify that both of these actions work and have the intended result.


## P3: Assign object names to every new backup widget

**Location:** `hypertts_addon/component_config_backup.py:39-40`

The new description label and root `layout_widget` lack stable `objectName` values, so live Anki GUI automation cannot reliably identify them.

Assign `hypertts_config_backup_*` names as required by `AGENTS.md:121-122`.
