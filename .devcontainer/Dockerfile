# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.222.0/containers/python-3/.devcontainer/base.Dockerfile

# for when we switch to python 3.9
# FROM mcr.microsoft.com/vscode/devcontainers/base:ubuntu-21.04
# use python 3.8 image for now
FROM mcr.microsoft.com/vscode/devcontainers/base:ubuntu-20.04

# [Optional] Uncomment this section to install additional OS packages.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends xfce4 xfce4-goodies tigervnc-common tigervnc-standalone-server \ 
    dbus-x11 xfonts-base xfonts-100dpi xfonts-75dpi \
    python3 python3-pip libnss3 libasound2 zstd libqt5x11extras5 xvfb ffmpeg

RUN git clone https://github.com/novnc/noVNC.git /opt/novnc
RUN git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify

# [Optional] Uncomment this line to install global node packages.
# RUN su vscode -c "source /usr/local/share/nvm/nvm.sh && npm install -g <your-package-here>" 2>&1

# [Optional] If your pip requirements rarely change, uncomment this section to add them to the image.
# required for novnc
RUN pip3 install numpy
# install packaged pip modules
COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
   && rm -rf /tmp/pip-tmp

# install anki versions 
ARG ANKI_DIR=/opt/anki
RUN mkdir ${ANKI_DIR}
ARG ANKI_2150_FILE=anki-2.1.50+beta8_02c580e4-linux-qt6.tar.zst
RUN cd ${ANKI_DIR} && wget -q https://apps.ankiweb.net/downloads/beta/${ANKI_2150_FILE} && tar xaf ${ANKI_2150_FILE} && rm ${ANKI_2150_FILE}
ARG ANKI_2149_FILE=anki-2.1.49-linux.tar.bz2
RUN cd ${ANKI_DIR} && wget -q https://github.com/ankitects/anki/releases/download/2.1.49/${ANKI_2149_FILE} && tar xjf ${ANKI_2149_FILE} && rm ${ANKI_2149_FILE}
RUN cd ${ANKI_DIR} && wget -q https://cloud-language-tools-storage.nyc3.digitaloceanspaces.com/collection.colpkg