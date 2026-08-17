# Why Anki Add-ons Lose Their Configuration — and What's Likely Happening to HyperTTS Presets

## TL;DR
- HyperTTS stores **all** presets and settings inside a single Anki addon-config blob that Anki persists to `meta.json` in the addon folder; the single most likely root cause of "lost presets" is that this whole file gets overwritten or corrupted — Anki's `writeAddonMeta` uses a **non-atomic** `open("w")` + `json.dump` write with no temp-file-and-rename, so a crash, disk-full, or cloud-sync race during a preset save can truncate the file and wipe every preset at once.
- The other high-probability mechanisms are: (a) two config locations diverging when a user has the addon installed both via AnkiWeb (folder `111623432`) and manually (a named folder), and (b) a serialization failure inside HyperTTS's own `save_preset` throwing before/while writing, leaving the on-disk config stale or partially written.
- The developer should add atomic writes with a rotating backup of the config, validate/serialize the config fully before overwriting the live copy, log every write/read of the config with preset counts, and give users a one-click "restore from backup" path — because Anki keeps no history of `meta.json` and add-on config is **not** covered by Anki's collection backups or AnkiWeb sync.

## Key Findings

**1. Issue #360 is a thin, aggregated report — not yet reproduced.** Opened by maintainer luc-vocab on Jul 3, 2026, titled "Configuration not being saved; presets being deleted after updates." The body states "a number of people report their HyperTTS configuration is not being saved, they need to enter their API key multiple times," and quotes two AnkiWeb reviews: "Addon frequently deletes presets" and "buggy, for example doesn't save my settings." It carries the labels **"need reproduction"** and **"priority."** There are no attached logs, Anki versions, platforms, or reproduction steps in the issue, and no comments. The developer is starting from symptom reports only.

**2. How HyperTTS stores its config.** HyperTTS keeps presets in an in-memory dict and serializes them into the Anki addon config under a presets key. A verbatim traceback in GitHub issue #225 ("Error on Archlinux, Anki 24.11 ModuleNotFoundError: No module named 'pkg_resources'", environment "Anki 24.11 (8e5efc59) … Python 3.13.1 Qt 6.8.1") shows `hypertts.py` line 666: `self.config[constants.CONFIG_PRESETS][preset.uuid] = preset.serialize()` — presets are keyed by UUID and live inside the addon config object, not in `col.set_config` and not as separate files in `user_files`. The shipped `config.json` at the addon root provides only defaults; user data (all presets, the HyperTTS Pro API key) is written by Anki to `meta.json`. This is consistent with the addon's own documentation, which tells users to safeguard data via Anki's export ("In Anki, click File → Export. Save the file on your hard drive. It's important to do this regularly (once a month)…" — HyperTTS Getting Started, AnkiWeb install code 111623432).

**3. Anki's config storage model (the mechanism everything hinges on).** Per the official add-on docs (addon-docs.ankiweb.net/addon-config.html): defaults ship in `config.json`; user edits are stored in `meta.json`; and — quoting verbatim — "When getConfig() is used after edits, meta.json is used preferentially. If a key is missing from meta.json's config, Anki will fall back on the default config," and "If no config.json file exists, getConfig() will return None - even if you have called writeConfig()." `writeConfig(__name__, config)` writes to `meta.json`. Critically, `meta.json` holds the **entire** addon config as one `"config"` key alongside `name`, `mod`, and `disabled`, and every `writeConfig` rewrites the whole file. Anki's `writeAddonMeta` (confirmed verbatim in the 2.1.15 source) is:
```python
def writeAddonMeta(self, dir, meta):
    path = self._addonMetaPath(dir)
    with open(path, "w", encoding="utf8") as f:
        json.dump(meta, f)
```
This is **not atomic** — `open(path, "w")` truncates immediately, then writes incrementally. A crash, power loss, disk-full, or antivirus/cloud lock mid-write leaves a truncated/invalid `meta.json`. On the next launch Anki's `addonMeta` catches the parse error and returns an empty dict (`except: return dict()`) — silently discarding every preset.

**4. `user_files` is the officially-preserved location — and HyperTTS does not use it for presets.** The docs state verbatim (addon-config.html § User Files): "Any files placed in this folder will be preserved when the add-on is upgraded. All other files in the add-on folder are removed on upgrade." `meta.json` is preserved across normal upgrades (it's not in the shipped zip), but it is NOT protected against the corruption, folder-duplication, and reinstall scenarios below.

## Details — Known Mechanisms by Which Anki Add-ons Lose Config

Ranked roughly by likely relevance to HyperTTS:

**A. Non-atomic `meta.json` write corrupted by a crash/kill/disk-full/cloud-sync race.** Because all presets are in one file rewritten wholesale on every save via a truncate-then-dump, an interruption during the write destroys the entire config, not one preset. Symptom match: "frequently deletes presets," "all presets gone." Evidence: Anki `writeAddonMeta` source (2.1.15); addon-config docs; `addonMeta`'s bare `except: return dict()` swallows corruption.

**B. Duplicate install locations (two configs).** AnkiWeb installs use the numeric folder `111623432`; manual/dev installs use a named folder. Config lives per-folder in that folder's `meta.json`. A user who has both (e.g., installed from AnkiWeb, then dropped in a manual build, or vice versa) edits presets in one folder while Anki loads the other — presets "disappear." Evidence: Anki addon-folders docs (AnkiWeb uses the item ID as folder name); HyperTTS extension docs referencing the `addons21/111623432/hypertts_addon/` path.

**C. Serialization/JSON errors causing silent or partial write failure.** Issue #225 shows `save_preset` → `serialize()` → databind → `pkg_resources` raising `ModuleNotFoundError`, and a secondary crash in the Sentry error handler (`TypeError: cannot pickle 'FrameLocalsProxy' object`). If serialization throws before/while persisting, the config on disk is left stale or half-written. The Review Heatmap tracker shows the analogous class of failure: `orjson.JSONEncodeError: Type is not JSON serializable: WrappedDict` when saving config (issues #87, #90, #103) — a non-serializable object silently blocks the save.

**D. Update/reinstall wiping the folder.** The addon-folders docs warn: "You should not store user data in the add-on folder, as it's deleted when the user upgrades an add-on." Normal upgrades preserve `meta.json`, but a **delete-and-reinstall** (as opposed to update), or a manual reinstall following the old glutanimate-style instructions ("delete the folder… optionally place meta.json back"), removes config. The glutanimate `import-bug-test` addon and review-heatmap issue #43 document a real Anki add-on import bug where config/meta could be lost on install.

**E. Add-on config is NOT synced and NOT in collection backups.** AnkiWeb sync does not include the `addons21` folder; add-on config is not part of the collection, so `col` backups and "Check Database" don't restore it. Users who "download from AnkiWeb" (one-way sync) or restore a backup expecting their presets back are disappointed — but this only wipes config if it's stored in the collection. HyperTTS stores it in `meta.json`, so sync/restore is not the direct cause, though users may conflate the timing.

**F. Cloud-sync / antivirus corruption of the Anki folder.** The Anki Manual (docs.ankiweb.net/files.html) warns verbatim: "We do not recommend you sync your Anki folder directly with a third-party synchronization service, as it can lead to database corruption when files are synced while in use." Cloud clients are independently documented to truncate files to 0 bytes — e.g., GitHub abraunegg/onedrive issue #1171 ("My .DOCX Was Overwriten With 0 Bytes"): "When I went to send my .DOCX… the filesize was 0 bytes… I believe the onedrive script mishandled this error and overwrote my .DOCX with an empty file." A `meta.json` caught mid-write while a cloud client races to upload/lock it is a plausible corruption path.

**G. Multiple Anki instances / profile issues.** Two Anki instances open at once, or config written from a background thread, can clobber concurrent writes because the last `writeConfig` wins and rewrites the whole file. Add-on config is global to the Anki base folder's `addons21`, not per-profile, so profile switching itself doesn't lose it — but concurrent instances can.

**H. Config-key/format changes across HyperTTS major versions.** Issue #157 ("Presets not accessible after upgrade due to major change in add-on") reports, verbatim: "I just upgraded to AnkiDesktop 23.12.1 and HyperTTS v1.08… I have 9 presets… When I click the buttons, I get a warning that I have no presets -- But my presets are… in the Config file." This is a migration/format-version problem where presets are physically present but unreadable by new code — presenting identically to "lost presets" from the user's side.

## Recommendations (staged, concrete)

**Stage 1 — Instrument (ship in next release, low risk):**
1. On every config read and write, log the preset count, config byte size, the target folder path (to detect duplicate-install case B), and HyperTTS + Anki versions. Log immediately before and after the `writeConfig` call.
2. Wrap `save_preset`/serialization in an explicit try/except that logs the full traceback locally (don't rely only on Sentry, which itself crashed in #225) and surfaces a clear "your preset was NOT saved" message rather than failing silently.
3. Add a diagnostic menu item that dumps the current config location, preset count, and whether a named-folder duplicate install exists.

**Stage 2 — Defensive persistence (highest-impact fix, addresses A/C/F):**
4. **Atomic write**: serialize the full config to a temp file in the same folder, `fsync`, then `os.replace()` over the target — never truncate the live file in place. (Anki's own write is not atomic, so do this in your own persistence layer or maintain a redundant copy.)
5. **Validate before overwrite**: fully serialize and re-parse the new config in memory first; if serialization fails, abort the write and keep the old config intact.
6. **Rotating backups**: on each successful save, also write a timestamped copy in `user_files/` (which the docs guarantee survives upgrades) — keep the last N. This gives a recovery path Anki does not provide.
7. **Never write an empty/short config over a non-empty one** without an explicit guard (e.g., refuse to persist 0 presets if the previous on-disk copy had many, unless the user explicitly deleted them).

**Stage 3 — Recovery + migration:**
8. On load, if `getConfig()` returns None/empty but a `user_files` backup exists, offer one-click restore.
9. Add explicit version-stamped config migration so major-version format changes (case H) never present as data loss.

**Questions to ask affected users (to disambiguate A–H):** exact Anki version and channel (AnkiWeb vs beta/manual); OS; whether the Anki2 folder is inside OneDrive/Dropbox/iCloud/Google Drive; whether they ever installed HyperTTS manually as well as from AnkiWeb; whether loss coincides with an Anki crash, an update, a sync, or a "download from AnkiWeb"; and whether the addon list shows two HyperTTS entries. Ask them to paste the contents of the addon's `meta.json`.

**Benchmarks that change the plan:** if logs show `writeConfig` succeeding with correct preset counts but the next launch reads zero → corruption/atomicity (A/F) is confirmed → prioritize Stage 2. If logs show two folder paths → case B → ship a duplicate-install detector/warning. If logs show serialization exceptions → case C → fix the serializer and add validation.

**Recovery paths to tell users now:** (1) If Anki is still open and hasn't restarted, the in-memory config may still hold their presets — export/copy immediately. (2) Check for a stale `meta.json` in any second (named) HyperTTS folder. (3) Restore `meta.json` from an OS-level or cloud "previous versions" snapshot (OneDrive/Dropbox/Time Machine/File History) — Anki itself keeps no history of it. (4) Going forward, use Anki's Add-ons → (select HyperTTS) → export config, or the addon's own backup, since AnkiWeb sync and collection backups will not save add-on config.

## Caveats
- Issue #360 contains no logs, versions, or repro steps; the ranking above is inferred from HyperTTS's storage design, the #225 traceback, analogous add-on bugs, and Anki's documented behavior — not from a confirmed HyperTTS reproduction.
- The verbatim `writeAddonMeta` non-atomic code is confirmed for Anki 2.1.15; the method was renamed to snake_case (`write_addon_meta`) in modern Anki and I could not verify whether recent versions added atomicity — the developer should confirm against current `qt/aqt/addons.py` before assuming Anki still writes non-atomically. (A forum thread on `meta.json` being saved with a plain un-indented `json.dump` suggests the pattern likely persists.)
- I could not open the tail of HyperTTS's `save_preset`/persistence method verbatim, so whether it calls `mw.addonManager.writeConfig` directly or via an `anki_utils` wrapper is a strong inference, not a confirmed quote. Confirm by inspecting `hypertts_addon/hypertts.py` and `hypertts_addon/anki_utils.py`.
- Some cited corroborating cases (Review Heatmap JSON-serialization errors, OneDrive 0-byte truncation) are from other software/add-ons and illustrate the mechanism class, not HyperTTS specifically.

### Primary sources
- HyperTTS issue #360: https://github.com/Vocab-Apps/anki-hyper-tts/issues/360
- HyperTTS issue #225 (traceback showing `save_preset` / `CONFIG_PRESETS`): https://github.com/Vocab-Apps/anki-hyper-tts/issues/225
- HyperTTS issue #157 (presets present in config but "no presets" after upgrade): https://github.com/Language-Tools/anki-hyper-tts/issues/157
- Anki add-on config docs: https://addon-docs.ankiweb.net/addon-config.html
- Anki add-on folders docs: https://addon-docs.ankiweb.net/addon-folders.html
- Anki `writeAddonMeta` source (2.1.15): https://sources.debian.org/data/main/a/anki/2.1.15+dfsg-3/aqt/addons.py
- Anki Manual, Managing Files (cloud-sync corruption warning): https://docs.ankiweb.net/files.html
- Anki Manual, Syncing (one-way sync / upload-download): https://docs.ankiweb.net/syncing.html
- Review Heatmap JSON-serialize save failures: https://github.com/glutanimate/review-heatmap/issues/90 , /issues/103 , /issues/87
- glutanimate import-bug-test (add-on import/meta loss): https://github.com/glutanimate/import-bug-test
- OneDrive 0-byte truncation precedent: https://github.com/abraunegg/onedrive (issue #1171)
- HyperTTS Getting Started (export/backup guidance, install code 111623432): https://www.vocab.ai/tutorials/hypertts-getting-started
- HyperTTS extensions repo (addon folder path): https://github.com/Vocab-Apps/anki-hyper-tts-extensions