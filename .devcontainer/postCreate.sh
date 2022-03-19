#!/bin/bash

# link workspace in anki addons
mkdir -p $HOME/.local/share/Anki2/addons21
ln -s /workspaces/anki-hyper-tts $HOME/.local/share/Anki2/addons21/anki-hyper-tts

# start up the processes we need directly

# clear all locks on X servers
sudo rm -f /tmp/.X*-lock
sudo rm -f /tmp/.X11-unix/X*

# vncserver on display :1
cp -rv $PWD/.devcontainer/config/.vnc $HOME/
/usr/bin/vncserver -SecurityTypes None -geometry 1920x1080 :1
# to shutdown:
# /usr/bin/vncserver -kill :1

# novnc
sudo ln -s $PWD/.devcontainer/config/novnc/index.html /opt/novnc/index.html
PIDFILE=/var/run/novnc.pid
DAEMON=/opt/novnc/utils/novnc_proxy
DAEMON_OPTS="--vnc localhost:5901"
start-stop-daemon --start --quiet --background --pidfile $PIDFILE --exec $DAEMON -- $DAEMON_OPTS

# xvfb
PIDFILE=/var/run/xvfb.pid
DAEMON=/usr/bin/Xvfb
# will run on display 2
DAEMON_OPTS=":2 -screen 0 1024x768x24 -ac +extension GLX +render -noreset"
start-stop-daemon --start --quiet --background --pidfile $PIDFILE --exec $DAEMON -- $DAEMON_OPTS
