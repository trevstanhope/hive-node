# Arduino Makefile
# 1. Place this file in the directory with the .ino:
# 2. TARGET is the name of the .ino file
# 3. BOARD_TAG is the model of Arduino, usually 'uno'
# 4. PORT is the serial port, usually '/dev/ttyS0' or '/dev/ttyACM0'
# 5. ARDUINO_LIBS are the included libraries
#	e.g. ARDUINO_LIBS = SoftwareSerial Servo	
# 6.. Compile the file to Arduino
# 	make clean
#	make
#	make upload

ARDUINO_DIR = /usr/share/arduino
TARGET = monitor_nodown
BOARD_TAG = alamode # for dev use 'uno'
ARDUINO_PORT = /dev/ttyS0 # for dev use '/dev/ttyACM0'
ARDUINO_LIBS = DHT stdio Wire Adafruit_BMP085
include /usr/share/arduino/Arduino.mk
