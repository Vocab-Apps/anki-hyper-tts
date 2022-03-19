#!/bin/bash

# link workspace in anki addons
mkdir -p $HOME/.local/share/Anki2/addons21
ln -s /workspaces/anki-hyper-tts $HOME/.local/share/Anki2/addons21/anki-hyper-tts

# VNC setup
sudo ln -s $PWD/.devcontainer/config/novnc/index.html /opt/novnc/index.html
cp -rv $PWD/.devcontainer/config/.vnc $HOME/