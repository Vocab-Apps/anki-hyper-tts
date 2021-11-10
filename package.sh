#!/bin/sh

VERSION_NUMBER=$1 # for example 0.1
GIT_TAG=v${VERSION_NUMBER}

# build web assets
cd web; npm run build || { echo 'npm build failed' ; exit 1; }
cd ..

echo "ANKI_LANGUAGE_TOOLS_VERSION='${VERSION_NUMBER}'" > version.py
git commit -a -m "upgraded version to ${VERSION_NUMBER}"
git push
git tag -a ${GIT_TAG} -m "version ${GIT_TAG}"
git push origin ${GIT_TAG}

# create .addon file
# remove meta.json, which contains private key
rm meta.json
rm -rf __pycache__
rm user_files/*.mp3
rm -rvf htmlcov/
ADDON_FILENAME=${HOME}/anki-addons-releases/anki-language-tools-${VERSION_NUMBER}.ankiaddon
zip --exclude "*node_modules*" -r ${ADDON_FILENAME} *


# if you need to undo a release:
# git tag -d v0.2
# git push --delete origin v0.2
