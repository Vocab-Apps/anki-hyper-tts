# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.222.0/containers/python-3/.devcontainer/base.Dockerfile

# python 3.9 image
FROM mcr.microsoft.com/vscode/devcontainers/base:ubuntu-21.04

# [Optional] Uncomment this section to install additional OS packages.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends xfce4 xfce4-goodies tigervnc-common tigervnc-standalone-server \ 
    dbus-x11 xfonts-base xfonts-100dpi xfonts-75dpi \
    python3 python3-pip libnss3 libasound2 zstd libqt5x11extras5 xvfb ffmpeg mplayer lame espeak-ng \
    fonts-arphic-ukai fonts-arphic-uming fonts-ipafont-mincho fonts-ipafont-gothic fonts-unfonts-core \
    nodejs npm

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
ARG ANKI_2154_FILE=anki-2.1.54-linux-qt6.tar.zst
RUN cd ${ANKI_DIR} && wget -q https://github.com/ankitects/anki/releases/download/2.1.54/${ANKI_2154_FILE} && tar xvaf ${ANKI_2154_FILE} && rm ${ANKI_2154_FILE}
RUN cd ${ANKI_DIR} && wget -q https://cloud-language-tools-storage.nyc3.digitaloceanspaces.com/collection.colpkg