#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ "$(id -u)" != 0 ]
then
    exec sudo sh ./install.sh
fi

apt-get update
apt-get install -y bluez rfkill cage seatd python3-dbus python3-gi python3-cairo python3-gi-cairo gir1.2-gtk-3.0 fonts-dejavu-core
systemctl enable --now bluetooth.service seatd.service
rfkill unblock bluetooth

if ! id ex30-display >/dev/null 2>&1
then
    adduser --system --group --no-create-home ex30-display
fi
# Raspberry Pi OS seatd grants socket access to the video group.
usermod -aG video,render,bluetooth ex30-display
install -d /opt/ex30-display
install -m 644 app.py bluez.py cluster.py stream.py /opt/ex30-display/
install -m 644 ex30-display.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable ex30-display.service
systemctl restart ex30-display.service
