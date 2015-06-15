#!/usr/bin/env python
"""
HiveMind Node
Developed by Trevor Stanhope
Hive sensor node based on RaspberryPi and Arduino.

TODO:
- Authenticate to aggregator?
- Authenticate to server?
- Validate data received from Arduino
- Add computer vision components
"""
#abcdefg recently edited by evan june 9th
__author__ = "Trevor Stanhope"
__version__ = "1.1a"

# Libraries
import zmq
import ast
import json
import os
import sys
try:
    import pyaudio
except Exception:
    pass
import cherrypy
import numpy as np
import random
import urllib2
from datetime import datetime
from serial import Serial, SerialException
from ctypes import *
from cherrypy.process.plugins import Monitor
from cherrypy import tools
import logging
import socket
import cv2
#audio libraries
from matplotlib.mlab import find
from matplotlib import pyplot as plt
import pyaudio
import numpy as np
import math

try:
    import Adafruit_DHT
except Exception:
    pass

try:
    import Adafruit_BMP.BMP085 as BMP085
except Exception:
    pass

# Constants
try:
    CONFIG_FILE = sys.argv[1]
except Exception as err:
    CONFIG_FILE = None

# Error Handling
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
def py_error_handler(filename, line, function, err, fmt):
  pass
C_ERROR_HANDLER = ERROR_HANDLER_FUNC(py_error_handler)

# Node
class HiveNode:

    ## Initialize
    def __init__(self, config):
        
        # Configuration
        if not config:
            self.REBOOT_ENABLED = False
            self.ZMQ_SERVER = "tcp://192.168.0.100:1980"
            self.ZMQ_TIMEOUT = 5000
            self.WAN_URL = "http://127.0.0.1:5000/new"
            self.ARDUINO_DEV = "/dev/ttyS0"
            self.ARDUINO_BAUD = 9600
            self.ARDUINO_TIMEOUT = 3
            self.MICROPHONE_CHANNELS = 1
            self.MICROPHONE_RATE = 44100
            self.MICROPHONE_CHUNK = 8192 
            self.MICROPHONE_FORMAT = pyaudio.paInt16
            self.MICROPHONE_RECORD_SECONDS = 2
            self.MICROPHONE_LOWPASS = 1000 # hz
            self.CAMERA_INDEX = 0
            self.CHERRYPY_PORT = 8081
            self.CHERRYPY_ADDR = "0.0.0.0"
            self.PING_INTERVAL = 1
            self.LOG_FILE = "log.txt"
            self.PARAMS = ["int_t","ext_t","int_h","ext_h","volts","amps","hz","db","pa"]
            self.HIVE_ID = socket.gethostname()
        else:
            self.load_config(config)

        # Initializers
        self.init_tasks()
        self.init_csv()
        self.init_zmq()
        self.init_logging()
        self.init_arduino()
        self.init_BMP()
        self.init_mic()
        self.init_cam()
    
    ## Load Config File
    def load_config(self, config):
        self.log_msg('CONFIG', 'Loading Config File')
        with open(config) as config_file:
            settings = json.loads(config_file.read())
            for key in settings:
                try:
                    getattr(self, key)
                except AttributeError as error:
                    self.log_msg('CONFIG', '%s : %s' % (key, str(settings[key])))
                    setattr(self, key, settings[key])
                    
    ## Initialize tasks
    def init_tasks(self):
        self.log_msg('ENGINE', 'Initializing cherrypy monitor tasks ...')    
        try:
            Monitor(cherrypy.engine, self.update, frequency=self.PING_INTERVAL).subscribe()
        except Exception as error:
            self.log_msg('ENGINE', 'Error: %s' % str(error))
    
    ## Initialize CSV backups
    def init_csv(self):
        self.NODE_DIR = os.path.dirname(os.path.abspath(__file__))
        for param in self.PARAMS:
            try:
                csv_path = os.path.join(self.NODE_DIR, 'data', param + '.csv')
                csv_file = open(csv_path, 'a')
                self.log_msg('CSV', 'Using EXISTING file for %s' % param)
            except Exception:
                self.log_msg('CSV', 'Using NEW file for %s' % param)
                with open(csv_path, 'w') as csv_file:
                    csv_file.write('date,val,\n') # no spaces!
                        
    ## Initialize ZMQ messenger
    def init_zmq(self):
        self.log_msg('ZMQ', 'Initializing ZMQ client ...')
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(self.ZMQ_SERVER)
            self.poller = zmq.Poller()
            self.poller.register(self.socket, zmq.POLLIN)
            msg = 'OK'
        except Exception as error:
            msg = 'Error: %s' % str(error)
        self.log_msg('ZMQ', msg)
    
    ## Initialize Logging
    def init_logging(self):    
        self.log_msg('LOG', 'Initializing logging ...')
        try:
            logging.basicConfig(filename=self.LOG_FILE,level=logging.DEBUG)
            msg = 'OK'
        except Exception as error:
            msg = 'Error: %s' % str(error)
        self.log_msg('LOG', msg)
    
    ## Initialize Arduino
    def init_arduino(self):
        self.log_msg('CTRL', 'Initializing controller ...')
        try:
            self.arduino = Serial(self.ARDUINO_DEV, self.ARDUINO_BAUD, timeout=self.ARDUINO_TIMEOUT)
            msg = 'OK'
        except Exception as error:
            msg = 'Error: %s' % str(error)
        self.log_msg('CTRL', msg)
    
    ## Initialize BMP Sensor
    def init_BMP(self):
        self.log_msg('BMP', 'Initializing BMP sensor ...')
        try:
            self.BMP085 = BMP085.BMP085()
        except Exception as error:
            self.log_msg('BMP', 'Error: %s' % str(error))
    
    ## Initialize camera
    def init_cam(self):
        self.log_msg('CAM', 'Initializing camera ...')
        try:
            self.camera = cv2.VideoCapture(self.CAMERA_INDEX)
            self.log_msg('CAM', 'OK')
        except Exception as error:
            self.log_msg('CAM', 'Error: %s' % str(error))

    ## Initialize audio
    def init_mic(self):
        self.log_msg('MIC', 'Initializing mic ...')
        """ part of revised code for audio processing """
        # Start audio stream
        try:
            self.p = pyaudio.PyAudio()
            self.microphone = self.p.open(
                format = self.MICROPHONE_FORMAT,
                channels = self.MICROPHONE_CHANNELS,
                rate = self.MICROPHONE_RATE,
                input = True,
                frames_per_buffer = self.MICROPHONE_CHUNK)
        except Exception as e:
            raise e

    ## Close Microphone
    def close_mic(self):
        """cleanly back out and release sound card."""
        self.p.close(self.microphone)

    # Capture Audio
    def capture_audio(self, trimBy=10):
        db = None
        hz = None
        try:
            # Capture Audio and convert to numeric
            audio = [] 
            for i in range(0, self.MICROPHONE_RATE / self.MICROPHONE_CHUNK * self.MICROPHONE_RECORD_SECONDS):
                audioString = self.microphone.read(self.MICROPHONE_CHUNK)
                audioNumeric = np.fromstring(audioString,dtype=np.int16)
                audio.append(audioNumeric)

            # Calculate Pitch
            pitch = []
            for signal in audio:
                crossing = [math.copysign(1.0, s) for s in signal]
                index = find(np.diff(crossing));
                f0 = round(len(index) * self.MICROPHONE_RATE /(2.0 * np.prod(len(signal))), 2)
                pitch.append(f0)
            pitch = np.array(pitch)
            pitch_lowpass = pitch[pitch < self.MICROPHONE_LOWPASS]
            hz = np.median(pitch_lowpass)

            # Calculate Decibels
            # audio.flatten() # pull data from record() thread
            left,right=np.split(np.abs(np.fft.fft(audio)),2)
            db = np.add(left,right[::-1])
            db = np.multiply(20,np.log10(db)) # db
            db = np.mean(np.multiply(20,np.log10(db))) # convert to dB
        except Exception as error:
            self.log_msg('MIC', 'Error: %s' % str(error))
        return { "db" : db, "hz" : hz}
    ## Capture Video
    def capture_video(self):
        self.log_msg('CAM', 'Capturing video ...')
        num_bees = None
        try:
            (s, bgr) = self.camera.read()
            if s:
                #! TODO Add computer vision analysis to function
                self.log_msg('CAM', 'OK')
            else:
                self.log_msg('CAM', 'Error: failed to get image')
        except Exception as error:
            self.log_msg('CAM', 'Error: %s' % str(error))
        result = {}
        return result

    ## Read Arduino (if available))
    def read_arduino(self):
        self.log_msg('CTRL', 'Reading from controller ...')
        try:
            string = self.arduino.readline()
            result = ast.literal_eval(string)
            self.log_msg('CTRL', 'OK: %s' % str(result))
        except Exception as error:           
            result = {}
            self.log_msg('CTRL', 'Error: %s' % str(error))
        return result
    
    ## Read DHT (if available)
    def read_DHT(self, pin=4):
        self.log_msg('DHT', 'Reading from DHT ...')
        try:
            sensor=Adafruit_DHT.DHT22
            humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)
            result = {
                "dht_t" : temperature,
                "dht_h" : humidity
            }
        except Exception as error:
            result = {}
            self.log_msg('DHT', 'Error: %s' % str(error))
        return result
        
    ## Read BMP (if available)
    def read_BMP(self):
        try:
            temperature = self.BMP085.read_temperature()
            pressure = self.BMP085.read_pressure()
            altitude = self.BMP085.read_altitude()
            sealevel_pressure = self.BMP085.read_read_sealevel_pressure()
            result = {
                "bmp_t" : temperature,
                "bmp_a" : altitude,
                "bmp_p" : pressure,
                "bmp_s" : sealevel_pressure
            }
        except Exception as error:
            result = {}
            self.log_msg('BMP', 'Error: %s' % str(error))
        return result
    
    ## Post sample to server
    def post_sample(self, sample):
        self.log_msg('REST', 'Posting to webserver ...')
        try:
            dump = json.dumps(sample)
            req = urllib2.Request(self.WAN_URL)
            req.add_header('Content-Type','application/json')
            response = urllib2.urlopen(req, dump)
            self.log_msg('REST', 'OK: %s' % str(response.getcode()))
            return response
        except Exception as error:
            self.log_msg('REST', 'Error: %s' % str(error))

    ## Send sample to aggregator
    def zmq_sample(self, sample):
        self.log_msg('ZMQ', 'Pushing to aggregator ...')
        try:
            dump = json.dumps(sample)
            self.socket.send(dump)
            socks = dict(self.poller.poll(self.ZMQ_TIMEOUT))
            if socks:
                if socks.get(self.socket) == zmq.POLLIN:
                    dump = self.socket.recv(zmq.NOBLOCK)
                    response = json.loads(dump)
                    self.log_msg('ZMQ', str(response))
                    result = response
                else:
                    self.log_msg('ZMQ', 'Error: Poll Timeout')
                    result = None
            else:
                self.log_msg('ZMQ', 'Error: Socket Timeout')
        except Exception as error:
            self.log_msg('ZMQ', 'Error: %s' % str(error))
        return result
            
    ## Save Data
    def save_sample(self, sample):
        self.log_msg('CSV', 'Saving sample to file ...')
        if sample:
            time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            for param in self.PARAMS:
                try:
                    csv_path = os.path.join(self.NODE_DIR, 'data', param + '.csv')
                    with open(csv_path, 'a') as csv_file:
                        csv_file.write(','.join([time, str(sample[param]), '\n']))
                except Exception as error:
                    self.log_msg('CSV', 'Error: Could not write key (%s)' % str(error))
        
    ## Generate blank sample
    def blank_sample(self):
        sample = {
            'type' : 'sample',
            'time' : datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'),
            'hive_id' : self.HIVE_ID
            }
        return sample

    ## Update Clock
    def update_clock(self, secs):
        self.TIME_ERROR = time.time() - secs
        self.log_msg('CLOCK', 'dt=%d' % secs)

    ## Log Message
    def log_msg(self, task, msg):
        date = datetime.strftime(datetime.now(), '%d/%b/%Y:%H:%M:%S')
        print('[%s] %s %s' % (date, task, msg))
    
    ## Shutdown
    def shutdown(self):
        self.log_msg('ENGINE', 'Shutting Down')
        try:
            self.arduino.close()
        except Exception as e:
            self.log_msg('CTRL', str(e))
        try:
            self.microphone.close()
        except Exception as e:
            self.log_msg('MIC', str(e))
        try:
            self.camera.release()
        except Exception as e:
            self.log_msg('CAM', str(e))
        os.system("sudo reboot")
            
    ## Update to Aggregator
    def update(self):
        sample = self.blank_sample()
        
        # Arduino
        arduino_result = self.read_arduino()
        sample.update(arduino_result)
        
        # Mic
        microphone_result = self.capture_audio()
        sample.update(microphone_result)
        
        # Camera
        camera_result = self.capture_video()
        sample.update(camera_result)
        
        # BMP
        BMP_result = self.read_BMP()
        sample.update(BMP_result)
        
        # DHT
        DHT_result = self.read_DHT()
        sample.update(DHT_result)
        
        print sample
        try:
            response = self.zmq_sample(sample)
            if response['type'] == 'clock':
                self.log_msg('ZMQ', 'Caught time update request', '')
                self.update_clock['secs']
            if response['type'] == 'config':
                self.log_msg('ZMQ', 'Caught Reload Config Request', '')
        except:
            if self.REBOOT_ENABLED:
                self.shutdown()
        self.post_sample(sample)
        self.save_sample(sample)

    ## Render Index
    @cherrypy.expose
    def index(self):
        with open('static/index.html') as html:
            return html.read()
    
# Main
if __name__ == '__main__':
    node = HiveNode(config=CONFIG_FILE)
    currdir = os.path.dirname(os.path.abspath(__file__))
    cherrypy.server.socket_host = node.CHERRYPY_ADDR
    cherrypy.server.socket_port = node.CHERRYPY_PORT
    conf = {
        '/': {'tools.staticdir.on':True, 'tools.staticdir.dir':os.path.join(currdir,'static')},
        '/data': {'tools.staticdir.on':True, 'tools.staticdir.dir':os.path.join(currdir,'data')},
        '/js': {'tools.staticdir.on':True, 'tools.staticdir.dir':os.path.join(currdir,'static','js')},
    }
    cherrypy.quickstart(node, '/', config=conf)
