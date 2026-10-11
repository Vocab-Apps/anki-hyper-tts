# Plan: support Anki 26.09's `NewEditor` (GitHub issue #371)

Date: 2026-09-29
Issue: https://github.com/Vocab-Apps/anki-hyper-tts/issues/371
Sentry: ANKI-HYPER-TTS-KMK (`AttributeError: 'NewEditor' object has no attribute 'note'`, 78 events / 32 users as of 2026-10-11, HyperTTS 3.6.0, Anki 26.08 – 26.09.3; see §11)

## 1. Summary

Anki 26.08 and later ship a second editor implementation, `aqt.editor.NewEditor` (upstream
commit `643187a05`, "Shift editor control to TypeScript", announced in the 26.08 release notes as
"an experimental rework of the editor ... can be enabled from Preferences>Experiments ... May affect
addon compatibility"; the local `~/src/anki` clone has no 26.08 tags, which is why it looks like a
26.09 change there). The legacy editor still exists (`aqt/editor_legacy.py`, re-exported by
`aqt/editor.py` through `from aqt.editor_legacy import *`), so on 26.08+ a user can get **either**
editor depending on a collection experiment flag and on whether Shift is held while opening the
window.

HyperTTS registers its three toolbar buttons through `gui_hooks.editor_did_init_buttons`. That hook
still fires for `NewEditor`, so the buttons appear, but every callback assumes the legacy object
model (`editor.note`, `editor.parentWindow.deckChooser`, `editor.set_note(note)` copying field
values). All three buttons (Add Audio, Preview Audio, Preset Mapping Rules) crash immediately.

The fix is an **editor adapter layer**: a small module that hides the difference between the legacy
synchronous `Editor` and the asynchronous, webview-owned `NewEditor`. The legacy code path must keep
working byte-for-byte on every Anki version HyperTTS supports (the oldest pinned test environment is
`requirements.anki-2.1.49.txt`, i.e. Anki 2.1.49).

## 2. What changed in Anki (verified against `~/src/anki`, tag `26.09.3-9-g1f7c8d7c4`)

### 2.1 Which editor is used

| Window | Code | Selection rule |
|---|---|---|
| Add Cards | `aqt/main.py:onAddCard` → `_open_new_or_legacy_dialog("AddCards", experimental)` | `NewAddCards` when `col.experiment_enabled(ExperimentFlag.SVELTE_EDITOR)` XOR Shift held; otherwise legacy `AddCards` |
| Edit Current | `aqt/main.py:onEditCurrent` → same helper | `NewEditCurrent` vs legacy `EditCurrent` |
| Browser | `aqt/browser/browser.py:setupEditor` (line ~618) | `aqt.editor.NewEditor` vs `aqt.editor.Editor`, same XOR rule |

Consequence: **we must dispatch on the editor instance type, never on the Anki version.** A 26.08+
user can have a legacy editor in one window and a `NewEditor` in another.

The experiment flag defaults to off (`Collection.experiment_enabled` reads the `experimentalFeatures`
config and returns `False` when unset) and no 26.08.x / 26.09.x point release changed the default.
So every user hitting ANKI-HYPER-TTS-KMK either turned on "Svelte editor" under
Preferences > Experiments or held Shift while opening the window. Sentry carries no tag that
distinguishes the two.

### 2.2 `NewEditor` (`qt/aqt/editor.py`)

What still exists and behaves like the legacy editor:

- `addButton(icon, cmd, func, tip, label, id, toggleable, keys, disables, rightside)` — same
  signature. `func` is wrapped in `call_after_note_saved(..., keepFocus=True)`.
- `addMode`, `editorMode`, `currentField`, `last_field_index`, `card`, `parentWindow`, `mw`, `web`.
- `currentField` is updated by `focus:N` / `blur:N` bridge commands. Add-on buttons call
  `preventDefault()` on `mousedown` (`ts/routes/editor/editor-toolbar/AddonButtons.svelte`), so
  clicking a HyperTTS button does **not** blur the field: `currentField` is still valid when our
  callback runs.
- `web` is an `AnkiWebView` → `web.selectedText()` and `web.eval()` / `web.evalWithCallback()` work.
- `set_note(note)` / `set_nid(nid, mid)` / `reload_note()` / `load_note(...)`.
- `editor.card` is set by `NewEditCurrent` and by the Browser (`browser.py:658`).

What is gone or different:

| Legacy | `NewEditor` |
|---|---|
| `editor.note: Note` (live, Python-owned) | **absent**. Only `editor.nid: NoteId \| None`. The live note is owned by the Svelte `NoteEditor` component. |
| — | `get_note_info(on_done)`: async, `evalWithCallback("getNoteInfo()")` → `NoteInfo(id, mid, fields)`. No tags, no deck. |
| `set_note(note)` pushes `note`'s field values into the webview | `set_note(note)` only stores `note.id` and calls `load_note(mid=note.mid)`, which **reloads from the backend by nid**. Field values of the passed object are ignored. In Add mode `nid` is `None`, so nothing HyperTTS computed would ever reach the editor. |
| `parentWindow.deckChooser.selectedId()` (Add Cards) | `NewAddCards` has **no** `deckChooser`. The deck chooser is `DeckChooser.svelte` inside `EditorChoosers.svelte`; its selection is not exposed to Python nor through `getNoteInfo()`. |
| `call_after_note_saved(cb)` always flushes | `call_after_note_saved(cb)`: **if `self.nid` is falsy (always the case in Add mode) it just schedules `cb` after 10 ms without saving**. Otherwise it appends `cb` to `_saved_callbacks` and evals `saveNow(keepFocus)`; the JS answers with bridge command `saved`. |

### 2.3 The TypeScript side (`ts/routes/editor/NoteEditor.svelte`)

Globals installed with `Object.assign(globalThis, {...})` in `onMount` that we can call from
Python via `editor.web.eval(...)`:

- `getNoteInfo()` → `{ id, mid, fields }` read from the internal `note` object.
- `saveNow()` → `async`: closes MathJax editor, commits tag edits, fires every pending field-save
  timer immediately, then `bridgeCommand("saved")` (non-legacy).
- `setFields(fieldNames, fieldValues)` → sets the per-field Svelte stores. Each store's subscriber
  calls `updateField(i, value)`, which (debounced 600 ms) copies the value into `note.fields[i]`
  and, outside Add mode, persists with `updateNotes`. Anki itself uses the same store mechanism to
  write fields from code (image occlusion: `fieldStores[ioFields.image].set(...)`), so the visible
  field updates.
- `reloadNote()`, `loadNote(args)`, `focusField(i)`.
- `window.bridgeCommand(cmd, cb?)` is available (`ts/lib/tslib/bridgecommand.ts`).

Important subtleties:

1. **Field values lag behind the UI by up to 600 ms.** `note.fields[i]` is only updated when the
   `ChangeTimer` fires or on `focusout`. Because our button click does not blur the field, anything
   typed in the last 600 ms is missing from `getNoteInfo()` unless `saveNow()` ran first. In Add
   mode Anki's own `addButton` wrapper does *not* run `saveNow()` (see `call_after_note_saved`).
2. `setFields()` overwrites **all** stores. Calling it with values read from a stale
   `getNoteInfo()` would revert whatever the user typed in the last 600 ms. Always `await saveNow()`
   before reading values that will be written back.
3. In edit modes, each debounced save calls `updateNotes({notes: [note]})` with the TS-side `note`
   object. If HyperTTS writes the note to the DB and the editor is **not** reloaded, the next
   keystroke in any field persists the stale TS copy and silently removes our sound tag.
4. `onOperationDidExecute`: when a `CollectionOp` reports `changes.noteText` and the mode is not
   `add`, the editor calls `reloadNote()`. A plain `col.update_note()` from a background thread
   does not broadcast op changes, so it does not trigger this.
5. Deck chooser DOM: `.deck-chooser .chooser-button` renders `selectedItem.name` (the full deck
   name, e.g. `Chinese::HSK1`). The chooser modal also renders
   `.deck-chooser .item-card.selected .item-title`. These are the only places the selected deck is
   observable from outside the component.

### 2.4 Bridge messages

`AnkiWebView._onBridgeCmd` runs `gui_hooks.webview_did_receive_js_message((False, None), cmd, context)`
before the editor's own `onBridgeCmd`. For `NewEditorWebView`, `context` is the `NewEditor`
instance (`set_bridge_command(self.onBridgeCmd, self)`). HyperTTS already registers a handler for
this hook in `gui.py` (`on_bridge_cmd`, welcome-message commands prefixed `hypertts:`), so we have
a clean, public channel for **JS → Python async results**, which `evalWithCallback` cannot provide
for promises (Qt's `runJavaScript` does not await a returned promise).

## 3. HyperTTS code affected

| Location | Legacy assumption |
|---|---|
| `hypertts_addon/gui.py:260-287` `run_hypertts_settings/preview/apply` | synchronous `get_editor_context(editor)` + `get_editor_deck_note_type(editor)` |
| `hypertts_addon/hypertts.py:335-365` `get_editor_context` | `editor.note`, `aqt.mw.col.models.get(...)` directly |
| `hypertts_addon/hypertts.py:367-377` `get_editor_deck_note_type` | `editor.note`, `parentWindow.deckChooser.selectedId()` |
| `hypertts_addon/hypertts.py:282-324` `editor_note_add_audio` | mutates `editor_context.note`, `col.update_note` if not add mode, `editor.set_note(note)` to refresh |
| `hypertts_addon/hypertts.py:476-515` `preview_all_mapping_rules` / `apply_all_mapping_rules` | call `get_editor_deck_note_type(editor_context.editor)` again |
| `hypertts_addon/component_batch.py:72-76`, `component_easy.py`, `component_source_easy.py`, `component_mappingrule.py`, `component_presetmappingrules.py`, `component_choosepreset.py` | read `editor_context.note` (a `Note`-like mapping: `keys()`, `[]`, `in`) — these keep working if the context carries a real `Note` snapshot |
| `hypertts_addon/anki_utils.py:356-373` `editor_set_field_value`, `show_loading_indicator`, `hide_loading_indicator` | legacy-only JS functions; **currently unused** (no callers) |

## 4. Design

### 4.1 Principles

- Detect the editor kind with
  `NewEditor = getattr(aqt.editor, 'NewEditor', None)` and `isinstance(editor, NewEditor)`.
  `getattr` keeps the import safe on Anki < 26.09. Anything that is not a `NewEditor` (including the
  test `MockEditor`) goes through the legacy path, which stays exactly as today.
- The legacy path is not refactored beyond wrapping existing code in an adapter class. Same calls,
  same order, same threads.
- Everything that touches the `NewEditor` webview runs on the main thread. Audio generation stays on
  the background thread as today.
- Every async callback into our code re-enters `hypertts.error_manager.get_single_action_context(...)`
  because the original `with` block in `gui.py` has already exited when the callback fires.
- The editor may be closed while we wait (window closed, browser switched note). Every callback
  checks `editor.web is not None` and, for existing notes, `editor.nid == snapshot.note_id`.

### 4.2 New module: `hypertts_addon/editor_adapter.py`

```python
@dataclasses.dataclass
class EditorSnapshot:
    note: anki.notes.Note          # real Note; NOT added to the collection in add mode
    note_id: Optional[int]         # None in add mode
    deck_note_type: config_models.DeckNoteType
    add_mode: bool
    current_field_index: Optional[int]
    selected_text: Optional[str]

class EditorAdapter(abc.ABC):
    editor: any
    add_mode: bool
    def is_alive(self) -> bool
    def get_snapshot(self, on_done: Callable[[EditorSnapshot], None], on_error: Callable[[Exception], None]) -> None
    def write_target_field(self, snapshot: EditorSnapshot, field_name: str,
                           compute_content: Callable[[str], str],
                           on_done: Callable[[], None], on_error: Callable[[Exception], None]) -> None

class LegacyEditorAdapter(EditorAdapter): ...
class NewEditorAdapter(EditorAdapter): ...

def for_editor(editor) -> EditorAdapter:
    NewEditor = getattr(aqt.editor, 'NewEditor', None)
    if NewEditor is not None and isinstance(editor, NewEditor):
        return NewEditorAdapter(editor, anki_utils)
    return LegacyEditorAdapter(editor, anki_utils)
```

`compute_content(current_target_field_value) -> new_value` is the pure "strip / keep only sound
tags / append `[sound:…]`" logic, extracted from `process_note_audio` (see 4.4). Passing a function
rather than a precomputed value lets the adapter apply it to the **freshest** field content at
write time, so edits made while audio was generating are not lost.

#### LegacyEditorAdapter (behaviour identical to today)

- `get_snapshot`: calls `on_done` synchronously with
  `note=editor.note`, `deck_note_type` from the current `get_editor_deck_note_type` logic
  (`parentWindow.deckChooser.selectedId()` in add mode, `editor.card.did` otherwise),
  `current_field_index=editor.currentField`, `selected_text=editor.web.selectedText()`.
  Note that `note` is the **live** `editor.note` object, as today.
- `write_target_field`: `note[field] = compute_content(note[field])`; `col.update_note(note)` unless
  add mode; then on main `editor.set_note(note)` guarded by `editor.web is not None` (the existing
  ANKI-HYPER-TTS-DWP guard). This is the current `editor_note_add_audio` tail, moved.

#### NewEditorAdapter

**Snapshot (`get_snapshot`)**, main thread:

1. Capture synchronously: `selected_text = editor.web.selectedText()`,
   `current_field_index = editor.currentField`, `nid = editor.nid`.
2. Allocate a request id, store `(on_done, on_error)` in a module-level `pending_requests` dict,
   start a timeout (`anki_utils.run_on_main_delayed(..., 5000)`) that fails the request with
   `errors.EditorNotResponding` if it is still pending.
3. `editor.web.eval(js)` with:

   ```js
   (async () => {
     try {
       await saveNow(true);                      // flush pending 600 ms field timers
       const info = getNoteInfo();
       const deckEl = document.querySelector('.deck-chooser .chooser-button');
       const payload = {
         id: info.id, mid: info.mid, fields: info.fields,
         deckId: info.deckId ?? null,            // forward compatible, see 4.6
         deckName: deckEl ? deckEl.textContent.trim() : null,
       };
       bridgeCommand('hypertts:editor_snapshot:' + REQUEST_ID + ':' + JSON.stringify(payload));
     } catch (e) {
       bridgeCommand('hypertts:editor_error:' + REQUEST_ID + ':' + JSON.stringify(String(e)));
     }
   })();
   ```

   `REQUEST_ID` is injected with `json.dumps`. `saveNow()` also emits `saved`, which just runs
   (and clears) `NewEditor._saved_callbacks` — harmless, and it is what Anki itself does.
4. The `webview_did_receive_js_message` handler (4.3) parses the payload and resolves the request:
   - `mid = int(payload['mid'])`, `fields = payload['fields']`.
   - **Existing note** (`payload['id']` non-empty and not `"0"`, and not add mode): the flush in
     step 3 already persisted the fields through `updateNotes`, so
     `note = col.get_note(NoteId(int(payload['id'])))` — a normal, complete `Note` (tags included).
     Sanity-check `note.fields == fields`; if they differ, log a warning and overwrite
     `note.fields` with the webview values (the webview is the source of truth for what the user
     sees).
   - **Add mode**: `note = anki.notes.Note(col, mid)` then `note.fields = list(fields)`. Never
     added to the collection. (Same construction Anki uses in `NewEditor.onCardLayout`.)
   - `deck_note_type`:
     - edit modes: `editor.card.did` if `editor.card` is set, else `note.cards()[0].did`
       (defensive — the Browser in notes mode still sets `editor.card`).
     - add mode: see 4.5.

**Write (`write_target_field`)**, main thread, called after audio generation finished on the
background thread:

- **Existing note** (Edit Current, Browser):
  1. Guard: `is_alive()` and `editor.nid == snapshot.note_id`; if the user navigated to another
     note, still persist to the snapshot's note (the user asked for it) but do not touch the editor.
  2. Take a fresh snapshot (step 3 above) so the editor's pending edits are flushed to the DB
     first — this prevents both "lost keystrokes" and subtlety 3 of §2.3 (a stale TS `note`
     overwriting us afterwards).
  3. `note = col.get_note(snapshot.note_id)`; `note[field] = compute_content(note[field])`.
  4. Persist with `aqt.operations.note.update_note(parent=editor.widget, note=note)
     .run_in_background()` (only on this path; the module exists since 2.1.45 but the legacy path
     keeps its current `col.update_note`). Benefits: an undo entry, the Browser table row refreshes,
     and the op broadcast makes the TS editor `reloadNote()` (§2.3.4).
  5. In the op's `success` callback, if `editor.nid == note.id`, call `editor.set_note(note)` as an
     explicit, idempotent refresh (belt and braces in case the op-handler reload is filtered for the
     initiating editor). Verify during GUI testing whether this causes a visible double reload; if it
     does, drop step 5.
- **Add Cards** (nothing may be written to the collection):
  1. Guard `is_alive()`.
  2. Resolve the target field index from the notetype: `names = [f['name'] for f in
     col.models.get(snapshot.note.mid)['flds']]`, `idx = names.index(field)`.
  3. Because `compute_content` must run on the freshest value, the write is a two-step exchange:
     a fresh snapshot (flushes + reads fields) → Python computes
     `new_value = compute_content(fresh.fields[idx])` → `editor.web.eval(js)`:

     ```js
     (async () => {
       await saveNow(true);
       const info = getNoteInfo();
       if (String(info.mid) !== EXPECTED_MID) {
         bridgeCommand('hypertts:editor_write:' + REQUEST_ID + ':"notetype_changed"'); return;
       }
       const values = info.fields.slice();
       values[IDX] = NEW_VALUE;
       setFields(FIELD_NAMES, values);
       bridgeCommand('hypertts:editor_write:' + REQUEST_ID + ':"ok"');
     })();
     ```

     All injected values go through `json.dumps`. The `saveNow` right before `setFields` makes
     `info.fields` equal to the visible stores, so only the target field changes.
  4. `notetype_changed` → raise a user-facing `errors.EditorNoteTypeChanged` (HyperTTSError,
     warning level) instead of writing into the wrong field.
  5. The sound file is already in `collection.media` (`get_collection_sound_tag` →
     `media_add_file`), so the `[sound:…]` tag plays in the editor and is kept when the user
     clicks Add (Anki's `addCurrentNoteInner` runs `saveNow()` which fires the 600 ms timer
     immediately and copies the store value into `note.fields`).

### 4.3 Bridge message handler

Extend `on_bridge_cmd` in `gui.py` (or register a second handler from `editor_adapter`) for:

- `hypertts:editor_snapshot:<request_id>:<json>`
- `hypertts:editor_write:<request_id>:<json>`
- `hypertts:editor_error:<request_id>:<json>`

Parse with `cmd.split(':', 3)` (JSON payloads contain colons). Pop the request from
`pending_requests`; unknown / already-timed-out ids are logged at `warning` and ignored. Return
`(True, None)` for all `hypertts:editor_` commands so they never reach `NewEditor.onBridgeCmd`
(which would `print("uncaught cmd", ...)` → stderr → Anki error dialog, see AGENTS.md logging
notes). Keep the existing welcome-message prefixes untouched; the `hypertts:editor_` prefix does not
collide with them.

### 4.4 Refactor in `hypertts.py`

1. **Split `process_note_audio`** (used by batch, realtime-free editor path, and tests) into:
   - `generate_note_sound_tag(batch, note, audio_request_context, text_override)`
     → `(source_text, processed_text, sound_tag, sound_file, full_filename)`: validates target
     field, computes source text, generates audio, adds media. Background-thread safe.
   - `compute_target_field_content(batch, current_content, sound_tag) -> str`: the pure
     strip/keep-only/append logic (lines 197-211 today). Unit-testable without Qt.
   - `process_note_audio` keeps its current signature and behaviour by composing the two plus the
     existing `note[target] = …` / `update_note` — batch mode and all existing tests are unaffected.
2. **`EditorContext`** (`config_models.py:697`): append two optional fields so every existing
   constructor call in the tests keeps working:
   ```python
   deck_note_type: Optional[DeckNoteType] = None
   editor_adapter: any = None     # EditorAdapter; None → editor_adapter.for_editor(editor)
   ```
   `note` now holds the snapshot `Note` (live object for legacy, copy for `NewEditor`).
3. **Replace `get_editor_context(editor)`** with a callback API:
   ```python
   def get_editor_context_async(self, editor, on_done: Callable[[EditorContext], None]) -> None
   ```
   It creates the adapter, calls `adapter.get_snapshot`, maps `current_field_index` to a name using
   `self.anki_utils.get_model(mid)` (instead of `aqt.mw.col.models.get`, which also makes it
   testable), and fills `deck_note_type`. For the legacy adapter `on_done` fires synchronously, so
   the legacy user experience is unchanged. Keep a thin synchronous `get_editor_context(editor)`
   for the legacy path only if a caller still needs it; otherwise remove it.
4. **`get_editor_deck_note_type(editor)`**: move its legacy body into `LegacyEditorAdapter`.
   `preview_all_mapping_rules` / `apply_all_mapping_rules` use `editor_context.deck_note_type`
   (falling back to the legacy computation when it is `None`, which only happens for contexts
   built by old tests).
5. **`editor_note_add_audio(batch, editor_context, text_input=None)`** — runs on the background
   thread today and must keep doing so:
   - compute `text_override` exactly as today;
   - `generate_note_sound_tag(...)` on the background thread (from `editor_context.note`);
   - `run_on_main(lambda: adapter.write_target_field(snapshot, target_field,
     lambda current: self.compute_target_field_content(batch, current, sound_tag), on_done, on_error))`;
   - `play_sound(full_filename)` as today.
   - Errors raised inside `write_target_field` callbacks are reported through
     `error_manager.get_single_action_context('Adding Audio to Note')`.
   - For the legacy adapter the net effect must equal today's code: mutate note, `update_note` if
     not add mode, `editor.set_note(note)`.
6. **`preview_note_audio_editor`**: unchanged; it only reads `editor_context.note` and
   `selected_text`, which the snapshot provides.

### 4.5 Add Cards: selected deck

Resolution order in `NewEditorAdapter`:

1. `payload['deckId']` if present (future-proofing for an upstream change, 4.6).
2. `payload['deckName']` from `.deck-chooser .chooser-button` → `col.decks.id_for_name(name)`.
   (Filtered decks cannot be selected in the chooser — `includeFiltered: false` — so a name always
   maps to a normal deck.)
3. If neither resolves (Anki changed the DOM, or the chooser shows the `…` placeholder):
   **do not silently use `col.decks.current()`** (it can differ from the chooser, as the issue
   points out). Instead:
   - build `DeckNoteType(model_id=mid, deck_id=None)`: note-type rules still match
     (`MappingRule.rule_applies` only compares `deck_id` for `MappingRuleType.DeckNoteType`),
     deck-specific rules do not;
   - log `logger.warning('could not determine selected deck in NewAddCards ...')` (a Sentry
     breadcrumb, not an issue) and show a tooltip:
     "HyperTTS could not detect the selected deck; deck-specific rules were skipped.";
   - in the Preset Mapping Rules dialog, disable creation of deck-specific rules when
     `deck_id is None` (`component_presetmappingrules.py`, around the "new rule" code path that
     builds `MappingRuleType.DeckNoteType` from `deck_note_type`).

### 4.6 Upstream follow-up (optional, not blocking)

Open a PR / forum request against ankitects/anki to add `deckId` to `getNoteInfo()` (and
`NoteInfo`) in Add mode. Our JS already reads `info.deckId ?? null`, so no HyperTTS change will be
needed when it lands; the DOM scrape becomes a fallback.

### 4.7 `gui.py` button callbacks

```python
def run_hypertts_apply(editor):
    with hypertts.error_manager.get_single_action_context('Generating Audio'):
        if not component_choose_easy_advanced.ensure_easy_advanced_choice_made(hypertts):
            return
        def on_context(editor_context):
            with hypertts.error_manager.get_single_action_context('Generating Audio'):
                if hypertts.load_mapping_rules().use_easy_mode:
                    component_easy.create_dialog_editor(hypertts, editor_context.deck_note_type, editor_context)
                else:
                    hypertts.apply_all_mapping_rules(editor_context)
        hypertts.get_editor_context_async(editor, on_context)
```

Same pattern for Preview and Settings. `ensure_easy_advanced_choice_made` may open a modal dialog;
keep it **before** the snapshot so the snapshot reflects the state after the dialog closes.

### 4.8 Dead code

`anki_utils.editor_set_field_value`, `show_loading_indicator`, `hide_loading_indicator` have no
callers and reference legacy-only JS (`set_field_value`, ...). Remove them in this change (and their
mock counterparts if any) so nobody wires them to a `NewEditor`.

### 4.9 Dialog lifetime / staleness

The Easy dialog, the mapping-rule dialogs and the batch-editor dialog hold `editor_context` while
the user interacts with them. With the legacy editor, `note` is the live object; with `NewEditor` it
is a snapshot taken when the button was clicked. That is acceptable because:

- previews use the snapshot (what the user saw when they clicked);
- writes always go through `write_target_field`, which re-reads the freshest field value
  (§4.2) before applying the sound tag.

## 5. Compatibility matrix

| Anki | Editor | Path | Expected |
|---|---|---|---|
| 2.1.49 … 26.05 | legacy `Editor` (no `NewEditor` attribute) | `LegacyEditorAdapter` | identical to HyperTTS 3.6.0 |
| 26.08+ | legacy (experiment off, or Shift-inverted) | `LegacyEditorAdapter` | identical to 3.6.0 |
| 26.08+ | `NewEditor` in Edit Current | `NewEditorAdapter`, existing note | fixed |
| 26.08+ | `NewEditor` in Browser | `NewEditorAdapter`, existing note | fixed |
| 26.08+ | `NewEditor` in `NewAddCards` | `NewEditorAdapter`, add mode | fixed |

Import-time safety: no module may `from aqt.editor import NewEditor` or `import aqt.addcards.NewAddCards`
at import time; use `getattr(aqt.editor, 'NewEditor', None)`. `anki.notes.Note(col, mid)` and
`aqt.operations.note.update_note` are only called on the `NewEditor` path, so their availability on
old versions does not matter.

## 6. Error handling

New `HyperTTSError` subclasses in `errors.py` (add them to the hierarchy comment at the top of the
file, and keep them at warning level so they do not create Sentry issues when they are expected):

- `EditorNotResponding` — the webview did not answer a snapshot/write request within 5 s (editor
  closed, page reloading, or Anki changed the JS API). Message suggests retrying and, if it
  persists, holding Shift when opening the editor to use Anki's legacy editor.
- `EditorNoteTypeChanged` — note type switched in Add Cards while audio was generating.
- `EditorClosed` — adapter `is_alive()` false when a callback fires; log at `info`, no dialog (the
  user closed the window on purpose).

JS exceptions (`hypertts:editor_error:`) are wrapped in a generic `HyperTTSError` with the JS message
and reported through the normal error manager (these *are* unexpected and should reach Sentry).

## 7. Tests

All tests run with the existing Qt/pytest setup. The dev environment has Anki 26.08 installed
(`aqt.editor.NewEditor` exists), and `requirements.anki-2.1.49.txt` is available for the oldest
supported version.

### 7.1 Test doubles (`test_utils/testing_utils.py`)

- Keep `MockEditor` (legacy) as is; it gets `LegacyEditorAdapter` automatically because it is not
  a `NewEditor` instance → all existing editor tests keep passing unchanged. This is the main
  regression net for the legacy path.
- Add `MockNewEditor`: `nid`, `addMode`, `currentField`, `card`, `web` (a `MockNewEditorWebView`
  that records `eval()`d JS and lets the test answer by feeding a bridge command into the handler),
  `set_note()` recording calls, `widget`.
- Tests construct `editor_adapter.NewEditorAdapter(MockNewEditor(...), anki_utils)` directly and
  pass it as `EditorContext.editor_adapter`, so no `isinstance` monkeypatching is needed. One
  separate test asserts `for_editor()` returns `NewEditorAdapter` for a real `aqt.editor.NewEditor`
  subclass stub (skip if `aqt.editor` has no `NewEditor`) and `LegacyEditorAdapter` otherwise.
- `MockAnkiUtils` needs `update_note_op(...)` (or whatever wrapper we put around
  `aqt.operations.note.update_note`) and `get_note_by_id` already exists.

### 7.2 New tests

`tests/test_editor_adapter.py`:

1. Legacy snapshot: add mode uses `parentWindow.deckChooser.selectedId()`, edit mode uses
   `card.did`, `note` is the live editor note.
2. NewEditor snapshot, existing note: JS contains `saveNow` and `getNoteInfo`; feeding
   `hypertts:editor_snapshot:<id>:{"id": "<nid>", "mid": "<mid>", "fields": [...], "deckName": null}`
   yields a `Note` loaded from the collection, `deck_note_type.deck_id == card.did`,
   `current_field` name resolved from `currentField`.
3. NewEditor snapshot, add mode: `note.id == 0`/falsy, fields from payload, deck resolved from
   `deckName`; `deckId` wins over `deckName` when both present; unresolvable deck → `deck_id is
   None` and a warning.
4. Timeout: no bridge answer → `EditorNotResponding` delivered to `on_error`; a late answer is
   ignored.
5. Bridge handler returns `(True, None)` for `hypertts:editor_*` and passes other commands through
   (welcome-message commands still work).
6. `compute_target_field_content`: `remove_sound_tag`, `text_and_sound_tag`, sound-only — table
   test, pure function.

`tests/test_hypertts.py` / `tests/test_component_batch_editor.py` additions (mirroring the existing
`set_note_called` tests):

7. Existing note via `NewEditorAdapter`: after apply, collection note has the sound tag, the
   update went through the op wrapper, `set_note` called only when `editor.nid` still matches.
8. Existing note, editor switched to another nid during generation: DB updated, editor untouched.
9. Add Cards via `NewEditorAdapter`: nothing written to the collection; the emitted JS contains
   `setFields` with only the target index changed relative to the fresh snapshot; other fields
   preserved (feed a fresh snapshot whose non-target field differs from the original snapshot to
   prove unsaved edits survive).
10. Add Cards, note type changed → `EditorNoteTypeChanged`, no `setFields` emitted.
11. Easy mode + mapping-rules preview/apply end-to-end through `gui` callbacks with both mocks
    (`test_audio_rules.py` already has the legacy variant — parametrize it over both adapters).
12. Deck-specific rule skipped (and note-type rule applied) when `deck_id is None`.

### 7.3 Run on both Anki environments

```bash
pytest -n auto                                   # current aqt (26.08, has NewEditor)
# in the 2.1.49 venv (requirements.anki-2.1.49.txt)
pytest -n auto tests/test_editor_adapter.py tests/test_component_batch_editor.py tests/test_audio_rules.py tests/test_hypertts.py
```

The 2.1.49 run proves nothing imports `NewEditor` eagerly and the legacy path is untouched.

## 8. Manual / GUI verification (use the `anki-gui-automation` skill)

The dev machine has Anki source 26.09.3 and the automation harness in `scripts/gui_automation/`.
Enable the Svelte editor experiment on the throwaway profile, inject a note with AnkiConnect, then
for each of **Edit Current**, **Browser**, **Add Cards**, with both Easy mode and preset-rules mode:

1. Type text in a field and click Preview **within 600 ms** → preview speaks the new text (proves
   the `saveNow` flush).
2. Select a word inside a field, Preview → only the selection is spoken (verifies
   `web.selectedText()` works through the Svelte rich-text input; if it returns empty because of
   shadow DOM, add `selection` to the JS payload using the focused field's shadow root
   `getSelection()` and prefer it).
3. Add Audio → target field visibly shows `[sound:hypertts-….mp3]`; other fields unchanged,
   including text typed just before clicking.
4. Edit Current / Browser: close and reopen the note → sound tag persisted; type in another field
   afterwards → sound tag still there (verifies the stale-TS-note problem §2.3.3 is solved);
   Edit → Undo removes the sound tag.
5. Add Cards: change the deck in the chooser to a deck with a deck-specific rule → that rule's
   preset is used; click Add → the added note contains the sound tag; nothing was added to the
   collection before clicking Add.
6. Settings (gear) opens Preset Mapping Rules with the correct note type and deck.
7. Close the editor window while audio is generating → no traceback, no Sentry error.
8. Hold Shift when opening each window (legacy editor on 26.09) and repeat 1-6 → unchanged
   behaviour.
9. Run `scripts/gui_automation/teardown.sh`.

Also run the existing manual checks in `scripts/openbox_menu_hypertts` for the editor dialogs.

## 9. Implementation order

1. `compute_target_field_content` / `generate_note_sound_tag` split in `hypertts.py` + unit tests
   (no behaviour change; full test suite green).
2. `editor_adapter.py` with `LegacyEditorAdapter` only; route `gui.py` and `hypertts.py` through it
   (`get_editor_context_async`, `EditorContext.deck_note_type`). Full suite green on current aqt
   and on the 2.1.49 venv. This step must be a pure refactor.
3. `NewEditorAdapter` snapshot + bridge handler + timeout + errors; tests 2-5.
4. `NewEditorAdapter` write paths (existing note via op, Add Cards via `setFields`); tests 7-12.
5. Deck resolution fallback + Preset Mapping Rules dialog handling of `deck_id is None`.
6. Remove dead `anki_utils` editor JS helpers.
7. GUI verification (§8) on Anki 26.09 with and without the Svelte editor experiment.
8. Update `AGENTS.md` with a short "Editor integration" note: never touch `editor.note` /
   `deckChooser` directly, go through `editor_adapter`; mention the `saveNow` flush and the
   `hypertts:editor_` bridge prefix.
9. Release as a patch version; reply on the Crisp conversation and close #371 / resolve
   ANKI-HYPER-TTS-KMK after confirming the Sentry event rate drops.

## 10. Risks and open questions

- **Private-ish JS API.** `saveNow`, `getNoteInfo`, `setFields` are globals Anki installs for its own
  Python side, not a documented add-on API; the deck chooser CSS classes are pure implementation
  detail. Mitigations: timeout + clear error, `deckId` forward compatibility, the §4.5 deck fallback,
  and GUI tests to run on each new Anki release. Check `NoteEditor.svelte` diffs when bumping.
- **`setFields` bypasses `encodeIriPaths`.** Irrelevant for `[sound:…]` tags (not IRIs), but do not
  reuse this path to write HTML with media `src` attributes.
- **Undo semantics change** on the `NewEditor` existing-note path (we now create an undo entry);
  the legacy path keeps its current behaviour. This is an improvement, but mention it in the
  release notes.
- **Image occlusion notetypes** in the new editor manage fields through their own stores; adding
  audio to an IO note in Add Cards should be tested once, but is not a target use case.
- **Selection inside shadow DOM** (§8 step 2) — the only piece of legacy behaviour that may need a
  JS-side fallback; to be confirmed during GUI testing.

## 11. Upstream context (collected 2026-10-11)

### 11.1 Sentry breakdown of ANKI-HYPER-TTS-KMK by Anki version (last 90 days)

| `anki_version` | events | users |
|---|---|---|
| 26.08.1 | 42 | 18 |
| 26.08 | 8 | 3 |
| 26.09 | 17 | 5 |
| 26.09.2 | 7 | 3 |
| 26.09.3 | 6 | 4 |

Most hits come from 26.08.x, consistent with the editor shipping in 26.08. The issue is currently
in Sentry's "ignored / archived until condition met" state.

### 11.2 GitHub (ankitects/anki)

- **PR #4029 "Shift editor control to TypeScript"** (abdnh, merged 2026-07-03) —
  https://github.com/ankitects/anki/pull/4029. The design discussion. abdnh's known-issues list
  ends with "The elephant in the room: Add-on compatibility" (unchecked). On add-on APIs:
  "`editor.addButton()` will keep working. Most editor hooks are broken in this PR right now
  though, and we still need to think about reducing add-on breakages (and probably introduce a
  JS API)." dae asked for a transition period with both editors and a Shift toggle, "hoping that
  it's something we'd have in place for <6 months". Before merge dae noted the PR used the new
  editor by default and asked to default to the old one; abdnh confirmed "It's disabled by default
  and will be put behind a preferences toggle (#4871)".
- **Issue #3830 "Shift editor control from Python to TypeScript"** (dae) —
  https://github.com/ankitects/anki/issues/3830. Motivation: stop pushing note data from
  `editor.py` via `eval()`, let the JS side pull from mediasrv, enable reuse in the mobile clients
  and a future Svelte browser. Explicit warning: "Add-ons currently rely on Python hooks and monkey
  patching to alter editor behaviour, and it may not be possible to preserve existing
  functionality in a backwards-compatible way."
- **Issue #5121 "New editor compatibility issues for add-ons"** (hssm, multi-column-note-editor
  author, 2026-07-08, closed) — https://github.com/ankitects/anki/issues/5121. Reports exactly our
  breakage: `NewEditor` has no `note` attribute, only `nid`; `editor_did_load_note` does not fire
  for Add Cards. abdnh: "The new editor is completely experimental - no guarantees about add-on
  compatibility or whether it'll stay in the next few versions" and "There will be a proper
  announcement/migration guide when it's ready if needed." abdnh is collecting add-on developer
  feedback via a Google form linked in that thread.
- **Issue #4871** — https://github.com/ankitects/anki/issues/4871. Design of the Preferences
  "Experiments" tab that gates the editor; implemented in PR #5057 (Luc-Mcgrady). The flag is
  stored per collection in the `experimentalFeatures` config and only takes effect after restart.
- **Issue #5202 "Review design of experimental editor components"** (abdnh, open) —
  https://github.com/ankitects/anki/issues/5202. All UI introduced by #4029 (including the Svelte
  deck/notetype choosers our §4.5 DOM scrape depends on) is awaiting design review and may change.
- Open bugs against the new editor: #5569 (duplicate audio playback when attaching/recording
  audio), #5226 (focus jumps back when duplicate status changes). Closed: #5567 (base64 images).
- Related 26.09 fixes: #5337 audio copy & paste, #5329 pasted/dropped audio not playing, #5373
  Add/Edit screens not closing, #5568 pasted images, #5348 "Ensure editor is initialized before
  triggering browser hooks", #5255 "Unhook AnkiWebView when destroyed" (dead
  `operation_did_execute` handlers after #4029 caused `RuntimeError`s with several add-ons).
- Release notes: 26.08 — https://github.com/ankitects/anki/releases/tag/26.08 (announces the
  experimental editor and the Experiments section). 26.09 —
  https://github.com/ankitects/anki/releases/tag/26.09 (only experimental-editor fixes; the add-on
  compatibility note is about `anki.importing` / `anki.exporting` removal, unrelated).
- HyperTTS: https://github.com/Vocab-Apps/anki-hyper-tts/issues/371 is the only public report of
  the `'NewEditor' object has no attribute` error for any add-on found on GitHub or the forums.

### 11.3 Anki forums

- **Svelte note editor dialogs** — https://forums.ankiweb.net/t/svelte-note-editor-dialogs/70603
  (derdilla, 2026-08-05). Complaint that the in-page deck / notetype choosers are awkward. abdo:
  design is preliminary, will get a designer review "once there's a release plan", and "add-on
  support still needs to be looked into". Confirms the chooser UI is expected to change.
- **Anki 26.09 Beta 1** — https://forums.ankiweb.net/t/anki-26-09-beta-1/70808 and
  **Anki 26.09 Release** — https://forums.ankiweb.net/t/anki-26-09-release/71024: no editor
  discussion at all.
- No forum thread mentions HyperTTS together with the new editor.

### 11.4 Implications for this plan

- Anki's stated position: the editor is opt-in, unsupported for add-ons, and both its Python API
  (`nid`, `get_note_info`) and its Svelte UI may change before a migration guide exists. The JS
  globals (`saveNow`, `getNoteInfo`, `setFields`) and the `.deck-chooser` selectors are therefore
  explicitly unstable; the timeout, `EditorNotResponding` and the §4.5 deck fallback are
  load-bearing, not defensive extras. Re-run §8 on every Anki release.
- The §4.6 upstream request (expose `deckId` from `getNoteInfo()` in Add mode) has a natural home:
  comment on #5121 or the Google form abdnh linked there, since that is where add-on feedback is
  being collected.
- Support reply for affected users until the fix ships: disable "Svelte editor" under
  Preferences > Experiments (restart required), or hold Shift when opening Add / Edit / Browse to
  get the legacy editor for that window.
