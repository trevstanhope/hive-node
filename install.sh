#!/bin/bash

# Dependencies
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install python -y
sudo apt-get install python-zmq -y
sudo apt-get install python-serial -y
sudo apt-get install python-cherrypy3 -y
sudo apt-get install python-pyaudio -y
sudo apt-get install python-alsaaudio -y

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
sudo cp -r libs/DHT /usr/share/arduino/libraries

# Connect to local wireless network
#sudo mv /etc/network/interfaces /etc/network/interfaces.backup
#sudo cp configs/interfaces /etc/network

# Apache2 port-forward 8081 to 80
#sudo cp configs/HiveMind /etc/apache2/sites-available/
#sudo a2ensite HiveMind

# Start on boot
#sudo cp configs/rc.local /etc/