# start up X server processes

# clear all locks on X servers
sudo rm -f /tmp/.X*-lock
sudo rm -f /tmp/.X11-unix/X*
touch $HOME/.Xauthority

# novnc
PIDFILE=/var/run/novnc.pid
DAEMON=/opt/novnc/utils/novnc_proxy
DAEMON_OPTS="--vnc localhost:5901"
rm $PIDFILE
start-stop-daemon --start --quiet --background --pidfile $PIDFILE --exec $DAEMON -- $DAEMON_OPTS

# xvfb
PIDFILE=/var/run/xvfb.pid
DAEMON=/usr/bin/Xvfb
# will run on display 2
DAEMON_OPTS=":2 -screen 0 1024x768x24 -ac +extension GLX +render -noreset"
rm $PIDFILE
start-stop-daemon --start --quiet --background --pidfile $PIDFILE --exec $DAEMON -- $DAEMON_OPTS

# vncserver
PIDFILE=/var/run/vncserver.pid
DAEMON=/usr/bin/vncserver
# will run on display 2
DAEMON_OPTS="-fg -SecurityTypes None -geometry 1920x1080 :1"
rm $PIDFILE
start-stop-daemon --start --quiet --background --pidfile $PIDFILE --exec $DAEMON -- $DAEMON_OPTS
