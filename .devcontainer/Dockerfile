# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.222.0/containers/python-3/.devcontainer/base.Dockerfile


FROM mcr.microsoft.com/vscode/devcontainers/base:ubuntu-21.04

# [Optional] If your pip requirements rarely change, uncomment this section to add them to the image.
# COPY requirements.txt /tmp/pip-tmp/
# RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
#    && rm -rf /tmp/pip-tmp

# [Optional] Uncomment this section to install additional OS packages.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends xfce4 xfce4-goodies tightvncserver dbus-x11 xfonts-base xfonts-100dpi xfonts-75dpi

RUN git clone https://github.com/novnc/noVNC.git /opt/novnc
RUN git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify

# [Optional] Uncomment this line to install global node packages.
# RUN su vscode -c "source /usr/local/share/nvm/nvm.sh && npm install -g <your-package-here>" 2>&1