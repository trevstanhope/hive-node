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
            self.MICROPHONE_CHUNK = 4096
            self.MICROPHONE_FORMAT = 8
            self.CAMERA_INDEX = 0
            self.CHERRYPY_PORT = 8081
            self.CHERRYPY_ADDR ="0.0.0.0"
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
        self.log_msg('CHERRYPY', 'Initializing Tasks')    
        try:
            Monitor(cherrypy.engine, self.update, frequency=self.PING_INTERVAL).subscribe()
        except Exception as error:
            self.log_msg('INIT TASKS', 'ERROR : %s' % str(error))
    
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
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(self.ZMQ_SERVER)
            self.poller = zmq.Poller()
            self.poller.register(self.socket, zmq.POLLIN)
            msg = 'OK'
        except Exception as error:
            msg = 'ERROR : %s' % str(error)
        self.log_msg('INIT ZMQ', msg)
    
    ## Initialize Logging
    def init_logging(self):    
        try:
            logging.basicConfig(filename=self.LOG_FILE,level=logging.DEBUG)
            msg = 'OK'
        except Exception as error:
            msg = 'ERROR : %s' % str(error)
        self.log_msg('INIT LOG', msg)
    
    ## Initialize Arduino
    def init_arduino(self):
        try:
            self.arduino = Serial(self.ARDUINO_DEV, self.ARDUINO_BAUD, timeout=self.ARDUINO_TIMEOUT)
            msg = 'OK'
        except Exception as error:
            msg = '\tERROR : %s' % str(error)
        self.log_msg('INIT ARDUINO', msg)
    
    ## Initialize Microphone
    def init_mic(self):
        try:
            asound = cdll.LoadLibrary('libasound.so')
            asound.snd_lib_error_set_handler(C_ERROR_HANDLER) # Set error handler
            mic = pyaudio.PyAudio()
            self.microphone = mic.open(
                format=self.MICROPHONE_FORMAT,
                channels=self.MICROPHONE_CHANNELS,
                rate=self.MICROPHONE_RATE,
                input=True,
                frames_per_buffer=self.MICROPHONE_CHUNK
            )
            self.microphone.stop_stream()
            msg = 'OK'
        except Exception as error:
            msg = 'ERROR : %s' % str(error)
        self.log_msg('INIT MIC', msg)
    
    ## Initialize camera
    def init_cam(self):
        self.camera = cv2.VideoCapture(self.CAMERA_INDEX)
        self.log_msg('INIT CAM', 'ERROR')

    ## Capture Audio
    def capture_audio(self):
        self.log_msg('MICROPHONE', 'Capturing Audio')
        rms_decibels = None
        dominant_hertz = None
        try:
            self.microphone.start_stream()
            data = self.microphone.read(self.MICROPHONE_CHUNK)
            self.microphone.stop_stream()
            wave_array = np.fromstring(data, dtype='int16')
            wave_fft = np.fft.fft(wave_array)
            wave_freqs = np.fft.fftfreq(len(wave_fft))
            dominant_peak = np.argmax(np.abs(wave_fft))
            dominant_hertz = self.MICROPHONE_RATE*abs(wave_freqs[dominant_peak])
            dominant_amplitude = np.sqrt(np.abs(wave_fft[dominant_peak])**2)
            dominant_decibels = 10*np.log10(dominant_amplitude)
            rms_amplitude = np.sqrt(np.mean(np.abs(wave_fft)**2))
            rms_decibels =  10*np.log10(rms_amplitude)
            sorted_peaks = np.argsort(np.abs(wave_fft))
            sorted_hertz = self.MICROPHONE_RATE*abs(wave_freqs[sorted_peaks])
        except Exception as error:
            self.log_msg('MICROPHONE', 'ERROR : %s' % str(error))
        result = {
            'db' : rms_decibels,
            'hz' : dominant_hertz
        }
        self.log_msg('MICROPHONE', str(result))
        return result
    
    ## Capture Video
    def capture_video(self):
        self.log_msg('CV2', 'Capturing Video')
        num_bees = None
        try:
            (s, bgr) = self.camera.read()
            if s:
                pass #! TODO Add computer vision analysis to function
            self.log_msg('CV2', 'OKAY: %s' % str(result))
        except Exception as error:
            self.log_msg('CV2', 'ERROR : %s' % str(error))
        result = {
            'bees' : num_bees
        }
        return result

    ## Read Arduino
    def read_arduino(self):
        self.log_msg('ARDUINO', 'Reading Arduino')
        try:
            string = self.arduino.readline()
            result = ast.literal_eval(string)
            self.log_msg('ARDUINO', 'OK : %s' % str(result))
        except Exception as error:
            result = {'arduino_error' : str(error)}
            self.log_msg('ARDUINO', 'ERROR : %s' % str(error))
        return result
    
    ## Post sample to server
    def post_sample(self, sample):
        self.log_msg('REST', 'Sending to Server')
        try:
            dump = json.dumps(sample)
            req = urllib2.Request(self.WAN_URL)
            req.add_header('Content-Type','application/json')
            response = urllib2.urlopen(req, dump)
            self.log_msg('REST', 'OK : %s' % str(response.getcode()))
            return response
        except Exception as error:
            self.log_msg('REST', 'ERROR : %s' % str(error))

    ## Send sample to aggregator
    def zmq_sample(self, sample):
        self.log_msg('ZMQ', 'Sending to Aggregator')
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
                    self.log_msg('ZMQ', 'ERROR : Poll Timeout')
                    result = None
            else:
                self.log_msg('ZMQ', 'ERROR : Socket Timeout')
        except Exception as error:
            self.log_msg('ZMQ', str(error))
        return result
            
    ## Save Data
    def save_sample(self, sample):
        self.log_msg('CSV', 'Saving Data to File')
        if sample:
            time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            for param in self.PARAMS:
                try:
                    csv_path = os.path.join(self.NODE_DIR, 'data', param + '.csv')
                    with open(csv_path, 'a') as csv_file:
                        csv_file.write(','.join([time, str(sample[param]), '\n']))
                except Exception as error:
                    self.log_msg('CSV', 'Could not write key: %s' % str(error))
        
    ## Generate blank sample
    def blank_sample(self):
        self.log_msg('MISC', 'Generating Blank Sample')
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
        self.log_msg('MISC', 'Shutting Down')
        try:
            self.arduino.close()
        except Exception as e:
            self.log_msg('CAMERA', str(e))
        try:
            self.microphone.close()
        except Exception as e:
            self.log_msg('CAMERA', str(e))
        try:
            self.camera.release()
        except Exception as e:
            self.log_msg('CAMERA', str(e))
        os.system("sudo reboot")
            
    ## Update to Aggregator
    def update(self):
        sample = self.blank_sample()
        arduino_result = self.read_arduino()
        sample.update(arduino_result)
        microphone_result = self.capture_audio()
        sample.update(microphone_result)
        camera_result = self.capture_video()
        sample.update(camera_result)
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
