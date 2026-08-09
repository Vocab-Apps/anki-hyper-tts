# Letting AI Agents Run and See a Full Anki Session for End-to-End Testing of HyperTTS

## TL;DR

- **Do not pick one approach — layer four.** Keep your current `pytest-qt` tests, add a **protocol/headless-import layer** (real `anki`+`aqt[qt6]` under `QT_QPA_PLATFORM=offscreen` or Xvfb + AnkiConnect for scripted drive), add an **accessibility (AT-SPI) textual widget-tree layer** so the agent reads structure as text instead of pixels, and add a **watchable Xvfb + window-manager + noVNC layer** so both the agent (via screenshots) and you (via browser) can see the live GUI. This maps cleanly onto how HyperTTS already tests (pytest + pytest-qt + real `anki`/`aqt[qt6]`, `qt_api=pyqt6`).
- **The single highest-leverage, lowest-token change is the AT-SPI accessibility tree.** Setting `QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1` exposes every HyperTTS widget (role, name, state, coordinates, actions) as structured text an agent can query with `dogtail`/`pyatspi` — far cheaper and more deterministic than screenshots. Pair it with strict `objectName` conventions on your `component_*.py` widgets so they are addressable.
- **For the webview parts of Anki, `QTWEBENGINE_REMOTE_DEBUGGING` is a first-class, officially-documented hook**, but note HyperTTS's own dialogs are native Qt widgets (not webviews), so AT-SPI/pytest-qt matter more for HyperTTS than CDP; use CDP/Playwright mainly if you test flows that live inside Anki's editor/reviewer/browser webviews.

## Key Findings

1. **Xvfb is the workhorse on Fedora.** Package `xorg-x11-server-Xvfb` provides `Xvfb`/`xvfb-run`. It creates an in-memory X11 display needing no GPU or monitor. Qt's `xcb` platform then renders into it, giving _full_ window-manager/focus/modality/input fidelity — unlike `offscreen`.
2. **`QT_QPA_PLATFORM=offscreen` is fastest for CI but silently breaks interaction.** Screenshots (`QWidget.grab()`) work; keyboard-focus, real modal-dialog behavior, drag/drop, and OpenGL contexts frequently do _not_. Multiple upstream reports confirm focus and OpenGL failures under offscreen; on headless Linux you often also need `QT_QUICK_BACKEND=software` and `LIBGL_ALWAYS_SOFTWARE=1`.
3. **A window manager materially reduces flakiness.** Under bare Xvfb with no WM, Qt modal dialogs and focus/stacking are unreliable. Adding a lightweight WM (openbox, i3, fluxbox, or mutter) fixes focus, raising, and modality — this is why Anthropic's own computer-use reference image runs a window manager (Mutter) and panel (Tint2) on top of Xvfb; its startup log reads verbatim "Xvfb started successfully on display :1 … starting tint2 on display :1 … starting mutter starting vnc PORT=5900 starting noVNC."
4. **Qt has a built-in VNC platform plugin.** `QT_QPA_PLATFORM=vnc` starts a VNC server (default port 5900) so a human/agent can view the app with zero extra services; a websocket build can even serve to a browser. It is convenient but less faithful than Xvfb+WM+x11vnc for complex WM behaviors.
5. **AnkiConnect is an ideal deterministic drive layer.** After install it "will initialize a minimal HTTP server running on port 8765 every time Anki executes" and by default binds only to 127.0.0.1 (override with `ANKICONNECT_BIND_ADDRESS`); the current API version is 5 and requests are HTTP POST JSON to `http://localhost:8765`. Actions include `guiAddCards`, `guiBrowse`, `guiEditNote`, `guiDeckReview`, `guiImportFile`, `storeMediaFile`, plus deck/note CRUD. An agent can set up decks/notes and trigger GUI dialogs by `curl` without touching pixels. A containerized "headless-anki" already ships this pattern (defaults to `QT_QPA_PLATFORM=vnc`).
6. **`QTWEBENGINE_REMOTE_DEBUGGING` is officially supported by Anki** (documented in Anki's add-on docs: set it to a port, then attach Chrome/CDP). It exposes Anki's webviews (deck browser, reviewer, editor) over the Chrome DevTools Protocol. Caveat: Playwright's `connect_over_cdp()` currently errors on QtWebEngine — Microsoft Playwright issue #36961 shows the attach aborting with "Protocol error (Browser.setDownloadBehavior): Browser context management is not supported," because Qt's DevTools server doesn't implement that method. Raw CDP or a patched attach is more reliable than vanilla Playwright.
7. **pytest-anki is stale; don't build on upstream.** Upstream `glutanimate/pytest-anki`'s last PyPI release is 1.0.0b7 (July 2022), it is PyQt5-era, its README states verbatim it is "currently undergoing a major rewrite and expansion of its feature-set" and has "only been confirmed to work on Linux so far" and "requires Python 3.8+." The actively maintained option is the **AnkiHubSoftware/pytest-anki fork** (updated Oct 2025). Its `anki_session` fixture yields `app` (AnkiApp/QApplication), `mw` (AnkiQt/QMainWindow), `user`, `base`, and `collection`, plus `load_addon`, `load_profile`/`profile_loaded`, and `deck_installed`, and advises marking tests `@pytest.mark.forked`.
8. **HyperTTS already does the hard part.** Your `pytest.ini` pins `qt_api=pyqt6`; `requirements.txt` installs the _real_ `anki` and `aqt[qt6]` plus `pytest-qt`/`pytest-xdist`; `conftest.py` sets `sys._pytest_mode`, fixes `sys.path` for `external/`, and calls `anki.lang.set_lang('en_US')`. You run `pytest`, `pytest -n auto`, `coverage run -m pytest`. So you already import the real Anki library — the gap is launching a _full `mw` GUI session_ and letting an agent observe/drive it.

## Details

### 1. HyperTTS's current state and where the gap is

Confirmed from the repo: HyperTTS uses `pytest` + `pytest-qt` with `qt_api=pyqt6` (pytest.ini: `qt_api=pyqt6`, `norecursedirs = external/*`, `addopts = --show-capture=no`), installs the genuine `anki` + `aqt[qt6]` PyPI packages, runs tests in parallel via `pytest-xdist` (`pytest -n auto`), and measures coverage. `conftest.py` is intentionally lightweight (sets `sys._pytest_mode = True`, prepends `external/` and root to `sys.path`, imports the real `anki` and sets `anki.lang.set_lang('en_US')`). `CLAUDE.md` documents the test commands (`pytest`, `pytest -n auto`, `coverage run -m pytest && coverage report`, `pytest tests/test_component_batchdownload.py`, `pytest --show-capture=all`); `TESTINGPROCEDURE.md` documents manual runs against the real Anki app with `HYPER_TTS_DEBUG_LOGGING=file` / `HYPER_TTS_DEBUG_LOGFILE`. There is a `.claude/skills/` directory and a `test_utils/` directory, and a sibling `anki-hyper-tts-extensions` repo carries an `AGENTS.md` for agents writing new TTS services.

Because your `component_*.py` GUI is _native Qt widgets launched from within Anki_, the two most valuable additions are (a) a way to spin up a real `aqt` main window headlessly and drive your components, and (b) a textual/visual channel so the agent can verify what rendered.

### 2. Virtual display / headless GUI options on Fedora

**Xvfb (recommended base).**

```bash
sudo dnf install -y xorg-x11-server-Xvfb
# one-shot wrapper (auto picks a free display, tears down after):
xvfb-run --auto-servernum --server-args="-screen 0 1920x1080x24" \
  python -m pytest tests/e2e
# or a long-lived display:
Xvfb :99 -screen 0 1920x1080x24 -ac &
export DISPLAY=:99
```

Xvfb shares code with the real X server, so `xcb` gives you real input events, focus, and modality. It has no GPU; force software GL for QtWebEngine (below).

**Add a window manager** (fixes modal/focus flakiness):

```bash
sudo dnf install -y openbox    # or i3, fluxbox, mutter
openbox &                       # after DISPLAY is set
```

**Watch it live via VNC + noVNC** (so you can watch the agent):

```bash
sudo dnf install -y x11vnc novnc python3-websockify
x11vnc -display :99 -nopw -forever -shared -rfbport 5900 &
# browser-accessible viewer:
websockify --web=/usr/share/novnc 6080 localhost:5900 &
# open http://localhost:6080/vnc.html
```

This is exactly the Xvfb + WM + x11vnc + noVNC stack Anthropic's computer-use reference image uses (it runs Mutter + Tint2).

**Qt's own platform plugins.**

- `QT_QPA_PLATFORM=offscreen` — no display needed; `QWidget.grab()`/`QScreen.grabWindow()` screenshots work, but focus, true modality, drag/drop, and OpenGL contexts often fail. Good for smoke tests and screenshot-on-failure in CI, not for faithful interaction.
- `QT_QPA_PLATFORM=vnc` — built-in VNC server on 5900; run headless and connect a viewer with zero extra daemons. Handy for quick human viewing; a containerized headless-Anki image defaults to this.
- `eglfs`/`linuxfb`/`minimal` — embedded/no-WM targets; not useful here.

**Wayland alternatives** (only if you specifically want Wayland): a headless wlroots compositor via `WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 sway`, or `weston --backend=headless-backend.so`, or `cage`, or `mutter --headless --virtual-monitor`, viewed with `wayvnc`. Interaction tools are `ydotool`/`wtype` and capture with `grim`/`slurp`. This is more moving parts than Xvfb for a Qt app; prefer Xvfb unless you have a Wayland-specific reason. (Note Anki's launcher prefers X11 and warns when falling back to Wayland.)

**Xephyr / Xdummy** are niche: Xephyr nests an X server inside another display (useful to debug locally); the Xorg dummy driver (`xorg-x11-drv-dummy`) supports RandR dynamic resize, which some apps prefer over Xvfb.

### 3. How the agent actually "sees" the screen

**(a) Screenshots the agent reads.** Claude Code can read image files, so the simplest loop is: dump a PNG to a known path and have the agent open it. Capture tools on X11: ImageMagick `import -window root out.png` (`dnf install ImageMagick`), `scrot`, `maim`, `xwd`, or `ffmpeg -f x11grab -video_size 1920x1080 -i :99 -frames:v 1 out.png`. For a specific widget you can also screenshot in-process with `widget.grab().save(path)` — this even works under `offscreen`. On Wayland use `grim`.

**(b) Video for review.** `ffmpeg -f x11grab -video_size 1920x1080 -i :99 -t 30 session.mp4` records a session for later human review.

**(c) Input simulation on X11:** `xdotool` (mouse move/click, type, key, window activate), `wmctrl` (window list/activate). On Wayland: `ydotool`/`wtype`.

**(d) MCP servers / computer-use loops.** Anthropic's computer-use reference (the Docker image with Xvfb + x11vnc + noVNC + an agent tool loop) is directly adaptable: swap the demo app for Anki. There are also Linux desktop-control MCP servers that expose screenshots + AT-SPI + input to any MCP client — e.g. `@agent-sh/computer-use-linux` (AT-SPI tree, screenshots, ydotool input; `get_app_state` returns a combined screenshot + accessibility tree with indexed elements), `kwin-mcp` (KDE/Wayland, AT-SPI2 tree so "no screenshots required for interaction"), and several Ubuntu-desktop-control MCPs. Fedora deps for the AT-SPI ones: `sudo dnf install at-spi2-core python3-gobject dbus-python wl-clipboard wtype`.

**(e) Accessibility tree — the token-efficient winner.** Qt ships an AT-SPI2 bridge on Linux. Force it on with `QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1` (and `QT_ACCESSIBILITY=1`). Then `dogtail`/`pyatspi`/Accerciser can enumerate every widget as structured text: role (button, text field, dialog), name/label, states (focused/enabled/visible), on-screen coordinates, and available actions (click, toggle). An agent querying "find the button named 'Add Audio' and click it" is far cheaper and more deterministic than reading a PNG. This is the single best fit for HyperTTS's native-widget dialogs. Requires a running AT-SPI bus (a D-Bus session), so run it under a real Xvfb+WM session (or `dbus-run-session`), not under `offscreen`.

### 4. End-to-end GUI automation frameworks for PyQt6

- **pytest-qt (already used).** `qtbot` drives `QTest.mouseClick`, `keyClicks`, `waitSignal`, `waitUntil` (deterministic waiting — use these instead of `sleep`). It runs fine under Xvfb; `qtbot.screenshot()` and `qtbot.stop()` aid debugging (with `--no-xvfb` via pytest-xvfb to pop up windows). Limit: it drives _your_ widgets in-process; it isn't a whole-desktop driver.
- **dogtail + AT-SPI** — real accessibility driving (see above); best for cross-process, whole-window flows an agent can reason about textually.
- **AnkiConnect** — protocol drive; deterministic; no pixels; ideal for fixture setup and triggering Anki dialogs.
- **Playwright/Selenium via CDP** for Anki's _webviews_ only, using `QTWEBENGINE_REMOTE_DEBUGGING`. Real caveat: Playwright's `connect_over_cdp()` fails against QtWebEngine (`Browser.setDownloadBehavior` unsupported — Playwright issue #36961); prefer raw CDP (websocket to `/devtools/page/<id>`) or a Chrome instance attached to the debugging port. HyperTTS's own dialogs are native widgets, so this matters only for flows inside Anki's editor/reviewer.
- **Image-based (SikuliX) / PyAutoGUI / autopy** — need a real display (Xvfb ok); brittle and pixel-dependent; not recommended as the primary agent channel.
- **Squish** (Qt Group, commercial) and **Robot Framework** — powerful but heavyweight; overkill for an open-source add-on and not agent-native.

### 5. QtWebEngine headless gotchas (critical for Anki)

Anki's main window, reviewer, editor, and deck browser are QtWebEngine webviews, so even testing a native HyperTTS dialog launched from Anki means QtWebEngine must initialize. On headless/containerized Fedora:

- **Disable the sandbox** when needed: `QTWEBENGINE_DISABLE_SANDBOX=1` (or `--no-sandbox`, or `QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox`). Required when running as root/in containers.
- **Force software rendering** (no GPU): `LIBGL_ALWAYS_SOFTWARE=1`, `QT_QUICK_BACKEND=software`; Fedora provides the Mesa llvmpipe/swrast software path via `mesa-dri-drivers` / `mesa-libGL`.
- **`/dev/shm` size in containers**: Chromium/QtWebEngine throws SIGBUS/crashes when `/dev/shm` is tiny. Docker/Podman default `/dev/shm` to exactly 64 MB, which is too small; run with `--shm-size=512m` (or larger).
- **The classic `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"`** on minimal Fedora is a missing-dependency problem. Install the xcb/xkb/GL stack:

```bash
sudo dnf install -y \
  libxkbcommon libxkbcommon-x11 \
  xcb-util xcb-util-cursor xcb-util-wm xcb-util-keysyms \
  xcb-util-image xcb-util-renderutil libxcb libX11-xcb \
  mesa-libGL mesa-libEGL mesa-dri-drivers \
  dbus-libs fontconfig \
  xdotool wmctrl ImageMagick x11vnc novnc python3-websockify \
  at-spi2-core python3-gobject dbus-python
```

Set `QT_DEBUG_PLUGINS=1` to diagnose exactly which shared library is missing.

### 6. Running a real Anki session headlessly

- **Isolated base folder per run** so you never touch a real profile: `anki -b /tmp/anki_e2e_base -p testprofile` (the `-b/--base` and `-p/--profile` args are stable; base defaults to `$XDG_DATA_HOME/Anki2`). Create a throwaway base each run for hermeticity.
- Avoid the profile picker by passing `-p`; create a fresh collection programmatically via `anki.collection.Collection(path)` for backend-only tests (this is how Anki's own `pylib` tests exercise the Rust backend without a GUI).
- Anki architecture to keep in mind: Rust core (`rslib`) → Python `pylib` (`import anki`) → Qt GUI (`aqt`, PyQt6) + TypeScript/HTML webviews. Backend-only assertions should use `anki.collection.Collection` in-memory; GUI assertions need `aqt` + a display.
- For agent-driven scripted setup, install **AnkiConnect** into the test base's `addons21/` and drive it over HTTP. The community "headless-anki" container demonstrates the whole pattern and defaults to `QT_QPA_PLATFORM=vnc`.

### 7. Containerization / reproducibility (Fedora-native)

- **Podman** (Fedora default) or Docker: build an image with Xvfb + openbox + x11vnc + noVNC + Anki + your addon, so every agent run is clean. Use `--shm-size=512m`. **toolbx/distrobox** are good for interactive dev parity.
- **Keep daemons alive** with `supervisord` or systemd user services (Xvfb → WM → x11vnc → websockify → Anki), the same ordering the noVNC community images use.
- **CI parity**: run the identical stack in GitHub Actions via `xvfb-run` (or the `GabrielBB/xvfb-action`). Since HyperTTS is Fedora-based locally but Actions is Ubuntu, keep the _env vars and command_ identical and only vary the package manager; better yet, run the same Podman/Docker image in CI so local and CI match exactly.

### 8. Agent ergonomics

- **One command, rich output.** Add a `make e2e` (or `scripts/e2e.sh`) that: starts Xvfb+WM(+x11vnc/noVNC), launches Anki with a temp base + AnkiConnect, runs a scenario, and dumps to a known dir: screenshots (`import`/`widget.grab()`), a **textual widget-tree dump**, and logs (`HYPER_TTS_DEBUG_LOGGING=file`). The agent runs one command and reads text first, images only when needed.
- **Dump the Qt tree as text** for cheap structural asserts:

```python
from aqt.qt import QApplication
for w in QApplication.allWidgets():
    if w.objectName():
        print(w.metaObject().className(), w.objectName(),
              w.isVisible(), w.isEnabled())
```

and/or `obj.dumpObjectTree()`. **Give every HyperTTS widget a stable `objectName`** (e.g. `hypertts_preset_name_edit`, `hypertts_add_audio_button`) in your `component_*.py` files — this makes both AT-SPI and `allWidgets()` addressable and turns brittle pixel-hunting into `find by name`.

- **Deterministic waiting**: `qtbot.waitUntil(lambda: widget.isVisible())` / `waitSignal`, never `time.sleep`.
- **AGENTS.md / CLAUDE.md**: document the harness invocation, where artifacts land, the widget naming scheme, and "prefer the widget-tree dump / AT-SPI over screenshots; only screenshot when a visual regression is suspected." HyperTTS already has a `CLAUDE.md` and `.claude/skills/` to extend.
- **Visual regression** (pytest-qt + pytest-image-diff / pytest-mpl style) is useful for catching layout regressions, but keep it out of the agent's inner loop — image diffs are token-heavy and flaky across font/DPI. Use them as a separate, human-reviewed CI gate.
- **Token/cost**: a widget-tree/AT-SPI dump is a few hundred tokens of text; a screenshot is thousands of tokens as an image and is lossy for asserting state. Default the agent to text; reserve screenshots for "does it _look_ right."

## Recommendations

**Stage 0 — now (hours):** Add stable `objectName`s to all `component_*.py` widgets and a `dump_widget_tree()` helper. This is the cheapest change with the biggest downstream payoff and unblocks every other layer.

**Stage 1 — Lightweight CI/offscreen (0.5 day).** Add an e2e path that launches the real `aqt` main window under `QT_QPA_PLATFORM=offscreen` with software GL (`LIBGL_ALWAYS_SOFTWARE=1`, `QT_QUICK_BACKEND=software`, `QTWEBENGINE_DISABLE_SANDBOX=1`), drives HyperTTS components with `qtbot`, and on failure dumps `widget.grab()` screenshots + the widget-tree text. Run it in GitHub Actions with `xvfb-run`. _Threshold to escalate:_ if focus/modality/dialog tests are flaky or fail under offscreen (they will for some), move those specific tests to Stage 2.

**Stage 2 — Full-fidelity watchable session (1 day).** Provide `make e2e` that runs Xvfb (`:99`, 1920×1080×24) + openbox + x11vnc + noVNC, launches Anki with a throwaway `-b` base and AnkiConnect, and exposes `http://localhost:6080/vnc.html` so you can watch the agent. The agent uses AnkiConnect for setup, `xdotool` for stray interactions, and `import` for screenshots. Package this as a Podman image (`--shm-size=512m`) for clean per-run environments and CI parity.

**Stage 3 — Accessibility-driven agent loop (1–2 days, highest ROI for autonomy).** In the Stage 2 session, set `QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1` and expose the AT-SPI tree to the agent — either via `dogtail`/`pyatspi` helper scripts you write, or by wiring an AT-SPI MCP server (e.g. `@agent-sh/computer-use-linux`) into Claude Code/Codex. The agent then reads/acts on named widgets textually and only screenshots to confirm visuals. This is the most reliable and token-efficient autonomous loop for HyperTTS's native dialogs.

**Stage 4 — Webview flows only, if needed.** For scenarios inside Anki's editor/reviewer/browser webviews, launch Anki with `QTWEBENGINE_REMOTE_DEBUGGING=9222` and drive via raw CDP (not vanilla Playwright, which fails on QtWebEngine). Skip this unless a feature genuinely lives in a webview.

**On pytest-anki:** don't adopt upstream `glutanimate/pytest-anki` (stale since 2022, PyQt5-era). If you want a fixture that boots a full `mw`, either lift the `anki_session` pattern from the **AnkiHubSoftware/pytest-anki** fork (updated Oct 2025, tracks current Anki) or — given you already import real `anki`/`aqt[qt6]` — write your own thin fixture that performs `aqt` setup with a temp base and tears it down with `@pytest.mark.forked` for isolation.

## Caveats

- **`offscreen` is a partial illusion**: screenshots render but input focus, true modal behavior, drag/drop, and OpenGL often don't — verified across multiple upstream bug reports. Don't trust green offscreen tests for interaction-heavy flows.
- **Playwright over CDP does not currently work cleanly against QtWebEngine** (`Browser.setDownloadBehavior` unsupported, per Playwright issue #36961); budget for raw CDP instead.
- **QtWebEngine in containers is fragile**: expect to set `--no-sandbox`/`QTWEBENGINE_DISABLE_SANDBOX=1`, software GL, and `--shm-size` ≥512 MB (default is only 64 MB) or you'll get opaque SIGBUS/renderer crashes.
- **AT-SPI needs a live D-Bus session and a real (Xvfb) display** — it won't work under bare `offscreen`. Coverage of custom-drawn widgets depends on Qt exposing them; standard `QWidget`s expose well, but verify your specific `component_*` widgets appear in `dogtail`'s tree.
- **Anki version churn is real**: PyQt6/Qt6 point releases (e.g. pyqt6-qt6 6.8.2) have caused Anki test crashes; HyperTTS already pins Qt versions in `requirements.txt` for this reason. Pin the Anki/aqt/PyQt versions in your e2e image and bump deliberately.
- **The Qt VNC platform plugin** is convenient but is a thin RFB server without a WM; for faithful modal/focus behavior prefer Xvfb + a real window manager + x11vnc.
- A few repo specifics (exact contents of `.claude/skills/` and `test_utils/`) couldn't be fetched directly due to GitHub anti-bot blocks; recommendations above are based on the confirmed `pytest.ini`, `requirements.txt`, `conftest.py`, `CLAUDE.md`, and `TESTINGPROCEDURE.md`.