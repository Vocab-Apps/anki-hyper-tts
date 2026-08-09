# GUI automation harness - machine setup

Everything the `scripts/gui_automation/` harness needs on a development machine. Written down so
it can be folded into ansible later.

## System packages (Fedora)

Already present on this machine before the harness was built:

```bash
sudo dnf install -y xorg-x11-server-Xvfb openbox at-spi2-core ffmpeg
```

Installed while building the harness (2026-08-09):

```bash
sudo dnf install -y x11vnc novnc python3-websockify xdotool wmctrl ImageMagick
```

`python3-gobject` and `dbus-x11` were installed too, for an AT-SPI based inspection channel that
turned out to be unnecessary — the `anki_gui_probe` add-on replaced it. **Do not put them in
ansible.** `dbus-x11` in particular drags in `dbus-daemon`, which is what lets
`at-spi-bus-launcher` / `at-spi2-registryd` start; the harness has no use for either, and
`start_anki.sh` now exports `QT_ACCESSIBILITY=0` / `NO_AT_BRIDGE=1`. To undo:

```bash
sudo dnf remove dbus-x11 dbus-tools dbus-daemon python3-gobject
```

What each is for:

| package | used for |
| --- | --- |
| `xorg-x11-server-Xvfb` | the virtual X display (`:99`) Anki renders into |
| `openbox` | window manager; without one, Qt modal dialogs get unreliable focus and stacking under Xvfb |
| `x11vnc` | serves the virtual display over VNC (port 5999) |
| `novnc` + `python3-websockify` | browser-accessible viewer at http://localhost:6099/vnc.html |
| `ImageMagick` | `import -window root` full-screen grabs in `screenshot.sh` |
| `xdotool` | checking the display is up (`getdisplaygeometry`), and real X11 input events if ever needed |
| `wmctrl` | window list in `status.sh` |
| `ffmpeg` | optional session recording (`ffmpeg -f x11grab -i :99 ...`) |

## Python packages

None. The harness scripts (`gui_probe.py`, `ankiconnect.py`, `setup_profile.py`) use only the
standard library, and `setup_profile.py` imports `aqt`/`anki` which are already in
`requirements.txt`. Nothing was added to `requirements.txt`.

## Third party add-ons

`AnkiConnect` is cloned on first run from `https://github.com/FooSoft/anki-connect` into
`/tmp/hypertts-gui-automation/cache/anki-connect` and copied into the throwaway profile with
`webBindPort` rewritten to 8766. No system-wide install, and the developer's own Anki profile is
never modified.

## Ports

| port | service | why non-default |
| --- | --- | --- |
| 8766 | AnkiConnect | the default 8765 could be a *real* Anki session; the harness must never drive the developer's own collection |
| 8767 | `anki_gui_probe` | development-only add-on, bound to 127.0.0.1 |
| 5999 | x11vnc | keeps the standard 5900 free |
| 6099 | noVNC / websockify | keeps the standard 6080 free |

## Paths

- runtime state: `/tmp/hypertts-gui-automation/` (`anki_base/`, `logs/`, `artifacts/`, `pids/`,
  `cache/`) — override with `HYPERTTS_GUI_WORKDIR`
- python environment: `/home/luc/python-env/anki-hyper-tts-3.13` — override with `HYPERTTS_VENV`
- vocabai QA credentials: `/home/luc/code/secrets/hypertts/clt_tts_vocabai_qa.sh` — override with
  `HYPERTTS_SECRETS_FILE`. `start_anki.sh` sources it (for
  `ANKI_LANGUAGE_TOOLS_VOCABAI_BASE_URL`) and `setup_profile.py` seeds
  `ANKI_LANGUAGE_TOOLS_API_KEY` into the throwaway profile's add-on config so HyperTTS Pro
  services work without going through the GUI. Nothing is written to the repo.
