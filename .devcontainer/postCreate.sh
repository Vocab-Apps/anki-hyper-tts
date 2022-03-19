#!/bin/bash

# setup vncserver
cp -rv $PWD/.devcontainer/config/.vnc $HOME/
touch ~/.Xauthority
rm -f /tmp/.X*-lock
rm -f /tmp/.X11-unix/X*
sudo ln -s $PWD/.devcontainer/services/vncserver /etc/init.d/vncserver
sudo update-rc.d vncserver defaults 99
sudo service vncserver start
# setup novnc
sudo ln -s $PWD/.devcontainer/config/novnc/index.html /opt/novnc/index.html
sudo ln -s $PWD/.devcontainer/services/novnc /etc/init.d/novnc
sudo update-rc.d novnc defaults 99
sudo service novnc start
# setup xvfb
sudo ln -s $PWD/.devcontainer/services/xvfb /etc/init.d/xvfb
sudo update-rc.d xvfb defaults 99
sudo service xvfb start