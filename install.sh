#!/bin/bash

# Dependencies
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install python -y
sudo apt-get install arduino arduino-mk -y
sudo apt-get install python-zmq -y
sudo apt-get install python-serial -y
sudo apt-get install python-cherrypy3 -y
sudo apt-get install python-pyaudio -y
sudo apt-get install python-alsaaudio -y
sudo apt-get install python-opencv -y
sudo apt-get install libasound2-dev alsa-utils -y

# Alamode
sudo cp configs/avrdude /usr/bin/avrdude
sudo cp configs/avrdude /usr/share/arduino/hardware/tools
sudo cp configs/avrdude.conf  /usr/share/arduino/hardware/tools
sudo cp configs/boards.txt  /usr/share/arduino/hardware/arduino
sudo cp configs/cmdline.txt /boot
sudo cp configs/inittab /etc
sudo cp configs/80-alamode.rules /etc/udev/rules.d
sudo chown root /usr/bin/avrdude /usr/share/arduino/hardware/tools/avrdude
sudo chgrp root /usr/bin/avrdude /usr/share/arduino/hardware/tools/avrdude
sudo chmod a+s /usr/bin/avrdude /usr/share/arduino/hardware/tools/avrdude
sudo cp -r libs/* /usr/share/arduino/libraries
sudo cp /usr/share/arduino/libraries/Wire/utility/* /usr/share/arduino/libraries/Wire/

# Connect to local wireless network
sudo cp configs/interfaces /etc/network

# Apache2 port-forward 8081 to 80
#sudo cp configs/HiveMind /etc/apache2/sites-available/
#sudo a2ensite HiveMind

# Start on boot
sudo cp -R ../hive-node /usr/share/
sudo ln -s /usr/share/hive-node/configs/hive-node /usr/bin
chmod +x /usr/bin/hive-node
sudo cp configs/rc.local /etc/
