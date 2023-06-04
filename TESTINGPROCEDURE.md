reset config

add single preset,
apply to notes directly, then close
run from browser/menu
run from editor

add  random preset,
run from browser/menu
run from editor

automated tests:
coverage run -m pytest
coverage html

coverage erase

# Testing on Windows
## Initial setup
* install Python 3.11 for windows
* install ffmpeg
* create python virtual env
* install requirements.txt and requirements.windows.txt
## Running
# go to C:\storage\dev\anki-hyper-tts
# need to activate virtual env
c:\storage\dev\env-anki-hyper-tts\Scripts\activate
# setup PATH
set PATH=C:\Users\Luc\AppData\Local\Programs\Anki;C:\Program Files\ffmpeg;%PATH%
# set tts keys
cat language_tools_tts_dev.sh | sed 's/export/set/g'
cat hypertts_testing_keys.sh  | sed 's/export/set/g'
# then
pytest test_tts_services.py  -k test_windows
