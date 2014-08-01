import serial, sys
baud = 9600

try:
    dev = sys.argv[1]
except Exception:
    dev = '/dev/ttyS0'
ard = serial.Serial(dev,baud)
while True:
    try:
        print ard.readline()
    except Exception:
        break
