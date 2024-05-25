# Manual testing Procedure
reset config

add single preset,
apply to notes directly, then close
run from browser/menu
run from editor

add  random preset,
run from browser/menu
run from editor

# automated tests
```
coverage run -m pytest
coverage html
coverage erase
python -m http.server --bind :: 8000
```

# Testing on Windows
## Initial setup
* install Python 3.11 for windows
* install ffmpeg
* create python virtual env
* create virtualenv
  * `cd c:\dev\python-env`
  * `python -m venv anki-hyper-tts`
  * `C:\dev\python-env\anki-hyper-tts\Scripts\activate`  
  * `cd C:\dev\python\anki-hyper-tts`
  * `c:\dev\python-env\anki-hyper-tts\Scripts\python.exe -m pip install --upgrade pip`
  * `pip install -r requirements.txt`
  * `pip install -r requirements.windows.txt`
* install requirements.txt and requirements.windows.txt
* directory junction for anki addon: `mklink /j C:\Users\Luc\AppData\Roaming\Anki2\addons21\anki-hyper-tts C:\dev\python\anki-hyper-tts`

## Running
### need to activate virtual env
C:\dev\python-env\anki-hyper-tts\Scripts\activate
### setup PATH
set PATH=C:\Users\Luc\AppData\Local\Programs\Anki;C:\Program Files\ffmpeg;%PATH%
### set tts keys
```
created this way
cat ~/secrets/cloudlanguagetools/post_deploy_tts_prod.sh | sed 's/export/set/g'
cat ~/secrets/hypertts/hypertts_services_keys.sh
```
execute ~/secrets/hypertts/hypertts_windows.bat
## go to hypertts directory
cd C:\dev\python\anki-hyper-tts
## then
pytest test_tts_services.py  -k test_windows

# Testing on MacOSX
## SSH Access (Scaleway)
* check python3 version, should be 3.9
* create virtual env: `mkdir python-env`
* `python3 -m venv anki-hyper-tts`
* `mkdir -p ~/python`
* sync hypertts files: `rsync -rv ~/python/anki-hyper-tts/ anki-dev-mac:~/python/anki-hyper-tts/`



## Required changes on XcodeClub
https://docs.ankiweb.net/platform/mac/display-issues.html
`echo software > ~/Library/Application\ Support/Anki2/gldriver6`

## Running on terminal with file logging
```
export HYPER_TTS_DEBUG_LOGGING=file
export HYPER_TTS_DEBUG_LOGFILE=`pwd`/hypertts.log
open /Applications/Utilities/Anki.app
```