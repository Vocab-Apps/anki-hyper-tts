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
```

# Testing on Windows
## Initial setup
* install Python 3.11 for windows
* install ffmpeg
* create python virtual env
* install requirements.txt and requirements.windows.txt

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
