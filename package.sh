#!/bin/sh

VERSION_NUMBER=$1 # for example 0.1
GIT_TAG=v${VERSION_NUMBER}

# build web assets
cd web; yarn build || { echo 'yarn build failed' ; exit 1; }
cd ..

echo "ANKI_HYPER_TTS_VERSION='${VERSION_NUMBER}'" > version.py
git commit -a -m "upgraded version to ${VERSION_NUMBER}"
git push
git tag -a ${GIT_TAG} -m "version ${GIT_TAG}"
git push origin ${GIT_TAG}

# create .addon file
# remove meta.json, which contains private key
rm meta.json
rm -rf __pycache__
rm user_files/*.mp3
rm user_files/*.ogg
rm -rvf htmlcov/
ADDON_FILENAME=${HOME}/anki-addons-releases/anki-hyper-tts-${VERSION_NUMBER}.ankiaddon
zip --exclude "*node_modules*" "*__pycache__*" "test_*.py" "*test_services*" "*.ini" "*.workspace" "*.md" "*.sh" requirements.txt "*.code-workspace" "web" -r ${ADDON_FILENAME} *


# if you need to undo a release:
# git tag -d v0.2
# git push --delete origin v0.2
