---
name: anki-gui-automation
description: "Develop and verify HyperTTS GUI screens against a real, running Anki instance: launch Anki headlessly on a throwaway profile, inject notes with AnkiConnect, read the live Qt widget tree as text, drive dialogs, screenshot them, and tear everything down"
user_invocable: true
---

# Agentic GUI development for HyperTTS

Use this whenever you add or change a HyperTTS dialog. pytest-qt tests prove the logic; this
harness proves the dialog is actually reachable, laid out correctly, and correct against a real
Anki collection (real notes, real `update_note`, real undo).

Everything runs on a virtual display against an **isolated Anki base folder and profile**, so the
developer's own Anki profile and collection are never touched. Both service ports are
deliberately non-default (AnkiConnect on 8766, not 8765) so the harness can never talk to a real
Anki session that happens to be open.

**You must run `scripts/gui_automation/teardown.sh` when you are done.** Leaving Xvfb, x11vnc,
websockify and a headless Anki running is the main failure mode of this workflow.

## The loop

```bash
cd scripts/gui_automation

./start_anki.sh                 # Xvfb + openbox + x11vnc + noVNC + Anki with HyperTTS
./ankiconnect.py seed --reset   # deck + note type + 5 notes with assorted sound tags
./ankiconnect.py browse         # open the browser on those notes
./gui_probe.py browser-select-all

./gui_probe.py actions --text Audio                   # what menu entries exist
./gui_probe.py trigger --text 'Remove Audio (Collection)...'   # open the dialog
./gui_probe.py windows                                # confirm it opened, and is modal
./gui_probe.py tree --window hypertts_remove_audio_dialog      # read the whole dialog as text
./gui_probe.py table --object-name hypertts_remove_audio_preview_table
./gui_probe.py screenshot --path /tmp/hypertts-gui-automation/artifacts/dialog.png \
    --window hypertts_remove_audio_dialog             # then Read the png

./teardown.sh                   # ALWAYS
```

**After editing any HyperTTS python file, run `./start_anki.sh --restart`.** The add-on is
symlinked into the profile, but Anki only imports it at startup. `--fresh` additionally throws
away the collection.

Read text first, screenshot second. `tree` costs a few hundred tokens and tells you state
(enabled, checked, current index, combo items); a screenshot costs thousands but is the only way
to catch layout problems. Both matter — the two bugs found while building the Remove Audio dialog
(a `QLabel` rendering `<b>` as literal text, and preview columns truncated by an even stretch)
were invisible in the widget tree and obvious in the screenshot.

Watch it live in a browser at http://localhost:6099/vnc.html while it runs.

## Widget naming convention (do this first, it unblocks everything)

Give every widget you create a stable `objectName`, prefixed `hypertts_<screen>_`:

```python
self.field_combobox = aqt.qt.QComboBox()
self.field_combobox.setObjectName('hypertts_remove_audio_field')
```

Name the dialog too (`self.setObjectName('hypertts_remove_audio_dialog')`) so `--window` can
target it. Without object names you have to address widgets by class + index path
(`RemoveAudioDialog/QGroupBox[0]/QComboBox[0]`), which breaks the moment the layout changes.
`hypertts_addon/component_remove_audio.py` is the reference implementation.

Older components (`component_batch.py`, `component_voiceselection.py`, …) have no object names
yet. For those, address widgets by `--class` + `--text`, or by the `path` printed by `tree`.

## scripts/gui_automation reference

| script | what it does |
| --- | --- |
| `start_display.sh` | Xvfb `:99`, openbox, x11vnc `5999`, noVNC `6099`. Idempotent. |
| `start_anki.sh [--restart\|--fresh]` | prepares the profile, launches Anki, waits for both ports |
| `setup_profile.py` | symlinks HyperTTS + installs AnkiConnect + `anki_gui_probe`, creates the profile |
| `stop_anki.sh` | stops only Anki, leaves the display up |
| `teardown.sh` | stops everything, cleans the X lock |
| `status.sh` | what is running, which ports answer, which windows are open |
| `screenshot.sh [name]` | full-screen grab into the artifacts dir (includes window decorations) |
| `ankiconnect.py` | inject/read collection data |
| `gui_probe.py` | inspect and drive the live GUI |

Runtime state lives under `/tmp/hypertts-gui-automation`: `anki_base/` (throwaway collection and
add-ons), `logs/anki.log`, `logs/hypertts.log` (HyperTTS debug logging is on), `artifacts/`
(screenshots), `pids/`.

### gui_probe.py

Inspect:

- `windows` — every top-level window: class, title, modal, active, geometry
- `tree [--window W] [--named-only] [--all] [--max-depth N]` — indented widget tree
- `info --object-name X` — one widget in detail
- `table --object-name X` — dump a `QTableView`/`QTreeView` model as rows (QVariant unwrapped)
- `actions [--text substring]` — every `QAction`, i.e. every menu entry
- `undo-status` — the label of the next undoable operation
- `note-fields --note-id N` — a note's fields straight from the collection

Drive:

- `click --object-name X [--no-wait]` — also `--class QPushButton --text Cancel`
- `set-text --object-name X --value '...'`
- `combo --object-name X --text '...'` (or `--index N`)
- `check --object-name X [--off]`
- `select-row --object-name X --row N`
- `trigger --text 'Menu entry...'` — opens dialogs; does not wait, by design
- `close --title '...' [--class ...]`, `undo`, `browser-select-all`, `browser-search --query ...`
- `screenshot --path P [--window W]` — `QWidget.grab()` of one window
- `raw '{"action": "eval", "params": {"expression": "mw.pm.name"}}'` — escape hatch, main-thread
  `eval` with `aqt`, `qt` and `mw` in scope

**Modal dialogs block the Qt main thread.** Any action that opens one must not wait for the main
thread, or the request times out. `trigger` defaults to not waiting; pass `--no-wait` to `click`
when the click opens a dialog (including a `QMessageBox` such as HyperTTS's "Save changes to
current preset ?" confirmation) or closes the window it lives on. When a probe call returns
`{"status": "pending"}` that is not an error: a modal is open and holding the main thread — call
`windows` to see it and deal with it.

Anki's own dialogs are reachable the same way, which is how you dismiss things like the add-on
startup error box:

```bash
./gui_probe.py tree --window QMessageBox
./gui_probe.py click --class QPushButton --text '&No' --window QMessageBox --no-wait
```

### ankiconnect.py

- `seed [--reset]` — creates the deck `HyperTTS Automation`, the note type
  `HyperTTS Automation Note` (fields Chinese / English / Sound / Sound English), stores dummy
  media files, and adds 5 notes: a lone HyperTTS sound tag, text plus a HyperTTS sound tag, a
  *foreign* sound tag (`external-recording.mp3`, i.e. audio HyperTTS did not generate), HyperTTS
  audio in two fields, and a note with no audio. Extend `seed_notes()` for new cases.
- `notes [--query Q]` — dump note fields, the cheapest way to assert what an operation did
- `browse [--query Q]` — open the browser on a query
- `invoke <action> [--params JSON]` — any AnkiConnect action

Two AnkiConnect gotchas, already handled in the helper but worth knowing:

- AnkiConnect is unmaintained and still assigns the deck through the legacy note-type dict, which
  modern Anki ignores, so `addNotes` lands cards in `Default`. `seed` moves them with `changeDeck`.
- Anki search syntax wants the quotes around the whole term: `"deck:HyperTTS Automation"`, not
  `deck:"HyperTTS Automation"`.

## Verifying a feature end to end

The pattern that actually proves a collection-modifying dialog works — this is how the Remove
Audio dialog was validated:

```bash
./ankiconnect.py notes            # state before
./gui_probe.py undo-status        # "" - nothing to undo yet
./gui_probe.py click --object-name hypertts_remove_audio_remove_button
./ankiconnect.py notes            # state after: only the intended fields changed
./gui_probe.py undo-status        # "HyperTTS: Remove Audio from Notes" <- undo support works
./gui_probe.py undo
./ankiconnect.py notes            # back to the original state
```

Undo support in HyperTTS comes from running the mutation inside
`anki_utils.run_in_background_collection_op(parent, update_fn, success_fn, undo_entry_name=...)`,
which wraps it in a custom undo entry. `update_fn` receives the collection and must call
`collection.update_note(note)`; never call `aqt.mw.col` directly from a dialog.

## pytest-qt tests are still required

The harness complements the test suite, it does not replace it. Every new dialog needs a
`tests/test_component_<name>.py` following the existing pattern:

- build a mock instance with `testing_utils.TestConfigGenerator().build_hypertts_instance_test_servicemanager('default')`
- component-level tests: `gui_testing_utils.build_empty_dialog()`, then `component.draw(dialog.getLayout())`
- full-workflow tests: register a `dialog_input_fn_map[constants.DIALOG_ID_<X>]` callback and call
  the `create_component_*` factory
- one `test_<name>_manual` guarded by `HYPERTTS_<X>_DIALOG_DEBUG=yes` which calls `dialog.exec()`,
  and a matching entry in `scripts/openbox_menu_hypertts` so the dialog can be eyeballed by hand

Run `pytest -n auto` before finishing. The `tests/test_tts_services/` tests hit real TTS APIs and
a couple can fail for unrelated network/speech-recognition reasons.

## Troubleshooting

- **"Add-on Startup Failed"** — HyperTTS raised during import. The add-on folder must be named
  `anki-hyper-tts` (it is what `constants.CONFIG_ADDON_NAME` looks up; any other name makes
  `getConfig()` return `None`). Read the message with
  `./gui_probe.py raw '{"action":"eval","params":{"expression":"[t.toPlainText() for w in qt.QApplication.topLevelWidgets() for t in w.findChildren(qt.QTextBrowser)]"}}'`
- **probe port not answering** — `tail -40 /tmp/hypertts-gui-automation/logs/anki.log`
- **port already in use** — a previous run was not torn down: `./teardown.sh`
- **table dump shows `QVariant` objects** — HyperTTS models return `QVariant`; the probe unwraps
  them, so this means the probe is stale: `./start_anki.sh --restart`
- **`import`/screenshot is black** — nothing is mapped on the display yet, or Anki is still
  starting; check `./status.sh`

## Requirements

System packages (Fedora, installed with `sudo dnf install`; see
`20260809_HYPERTTS_GUI_AUTOMATION_SETUP.md`):
`xorg-x11-server-Xvfb openbox x11vnc novnc python3-websockify xdotool wmctrl ImageMagick`

The helper scripts only use the python standard library, so there are no additions to
`requirements.txt`. `xdotool`/`wmctrl` are available for real X11 input events if a widget ever
resists `QWidget.click()`.

The harness deliberately does **not** use the AT-SPI accessibility tree — the probe is cheaper and
more precise — and `start_anki.sh` exports `QT_ACCESSIBILITY=0` / `NO_AT_BRIDGE=1` so Qt does not
publish the widget tree over D-Bus. Do not install `dbus-x11` / `at-spi2-core` for this workflow:
nothing here needs them.
