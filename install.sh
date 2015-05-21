#!/bin/bash

# Dependencies
echo "Installing dependencies ..."
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install build-essential -y
sudo apt-get install python -y
sudo apt-get install python-dev -y
sudo apt-get install arduino arduino-mk -y
sudo apt-get install python-zmq -y
sudo apt-get install python-serial -y
sudo apt-get install python-cherrypy3 -y
sudo apt-get install python-pyaudio -y
sudo apt-get install python-alsaaudio -y
sudo apt-get install python-opencv -y
sudo apt-get install libasound2-dev alsa-utils -y
sudo apt-get install python-smbus -y

# Alamode
echo "Would you like to install Alamode and libraries [y/n]?"
read ans
if [ $ans = y -o $ans = Y -o $ans = yes -o $ans = Yes -o $ans = YES ]
then
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
fi
if [ $ans = n -o $ans = N -o $ans = no -o $ans = No -o $ans = NO ]
then
echo "Skipping Arduino install"
fi

# Alamode
echo "Would you like to install DHT libraries [y/n]?"
read ans
if [ $ans = y -o $ans = Y -o $ans = yes -o $ans = Yes -o $ans = YES ]
then
    cd libs/Adafruit_Python_DHT
    sudo python setup.py install
    cd ../..
fi
if [ $ans = n -o $ans = N -o $ans = no -o $ans = No -o $ans = NO ]
then
echo "Skipping DHT install"
fi

# Alamode
echo "Would you like to install BMP libraries [y/n]?"
read ans
if [ $ans = y -o $ans = Y -o $ans = yes -o $ans = Yes -o $ans = YES ]
then
    cd libs/Adafruit_Python_BMP
    sudo python setup.py install
    cd ../..
fi
if [ $ans = n -o $ans = N -o $ans = no -o $ans = No -o $ans = NO ]
then
echo "Skipping BMP install"
fi

# Connect to local wireless network
echo "Would you like to configure the network [y/n]?"
read ans
if [ $ans = y -o $ans = Y -o $ans = yes -o $ans = Yes -o $ans = YES ]
then
sudo cp configs/interfaces /etc/network
fi
if [ $ans = n -o $ans = N -o $ans = no -o $ans = No -o $ans = NO ]
then
echo "Skipping network configuration..."
fi

# Start on boot
echo "Would you like the node to start on boot [y/n]?"
read ans
if [ $ans = y -o $ans = Y -o $ans = yes -o $ans = Yes -o $ans = YES ]
then
echo "Setting up start on boot ..."
sudo cp configs/rc.local /etc/
fi
if [ $ans = n -o $ans = N -o $ans = no -o $ans = No -o $ans = NO ]
then
echo "Skipping start on boot..."
fi
