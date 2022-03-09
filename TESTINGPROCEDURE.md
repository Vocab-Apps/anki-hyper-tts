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

# testing on windows
# go to C:\storage\dev\anki-hyper-tts
# need to activate virtual env
c:\storage\dev\env-anki-hyper-tts\Scripts\activate
# setup PATH
set PATH=C:\Program Files\Anki;C:\storage\dev\libav;%PATH%
# set tts keys
cat language_tools_tts_dev.sh | sed 's/export/set/g'
cat hypertts_testing_keys.sh  | sed 's/export/set/g'
# then
pytest test_tts_services.py  -k test_windows
