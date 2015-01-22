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
            self.ZMQ_ENABLED = True
            self.ZMQ_SERVER = "tcp://192.168.0.199:1980"
            self.ZMQ_TIMEOUT = 5000
            self.WAN_ENABLED = False
            self.WAN_URL = "http://hivemind.mobi/new"
            self.ARDUINO_ENABLED = True
            self.ARDUINO_DEV = "/dev/ttyS0"
            self.ARDUINO_BAUD = 9600
            self.ARDUINO_TIMEOUT = 3
            self.MICROPHONE_ENABLED = True
            self.MICROPHONE_CHANNELS = 1
            self.MICROPHONE_RATE = 44100
            self.MICROPHONE_CHUNK = 4096
            self.MICROPHONE_FORMAT = 8
            self.CAMERA_ENABLED = False
            self.CHERRYPY_PORT = 8081
            self.CHERRYPY_ADDR ="0.0.0.0"
            self.CHERRYPY_INTERVAL = 0.5
            self.CSV_ENABLED = False
            self.LOG_ENABLED = True
            self.LOG_FILE = "log.txt"
            self.PARAMS = ["int_t","ext_t","int_h","ext_h","volts","amps","hz","db","pa"]
            self.HIVE_ID = socket.gethostname()
            self.log_msg('Setting Default Configuration', 'OK')
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
        self.log_msg('Loading Config File', 'OK')
        with open(config) as config_file:
            settings = json.loads(config_file.read())
            for key in settings:
                try:
                    getattr(self, key)
                except AttributeError as error:
                    print('\t' + key + ' : ' + str(settings[key]))
                    setattr(self, key, settings[key])
        self.log_msg('Loading Config File', 'OK')
                    
    ## Initialize tasks
    def init_tasks(self):    
        try:
            Monitor(cherrypy.engine, self.update, frequency=self.CHERRYPY_INTERVAL).subscribe()
            msg = 'OKAY'
        except Exception as error:
            msg = 'ERROR : %s' % str(error)
        self.log_msg('Initializing Tasks', msg)
    
    ## Initialize CSV backups
    def init_csv(self):
        if self.CSV_ENABLED:
			for param in self.PARAMS:
				try:
					open('data/' + param + '.csv', 'a')
					print('\tUSING EXISTING FILE: ' + param)
				except Exception:
					print('\tCREATING NEW FILE: ' + param)
					with open('data/' + param + '.csv', 'w') as csv_file:
						csv_file.write('date,val,\n') # no spaces!
			self.log_msg('Initializing CSV Logs', 'OK')
                        
    ## Initialize ZMQ messenger                    
    def init_zmq(self):
        if self.ZMQ_ENABLED:
			try:
				self.context = zmq.Context()
				self.socket = self.context.socket(zmq.REQ)
				self.socket.connect(self.ZMQ_SERVER)
				self.poller = zmq.Poller()
				self.poller.register(self.socket, zmq.POLLIN)
				msg = 'OKAY'
			except Exception as error:
				msg = 'ERROR : %s' % str(error)
			self.log_msg('Initializing ZMQ', msg)
    
    ## Initialize Logging
    def init_logging(self):    
        if self.LOG_ENABLED:
			try:
				logging.basicConfig(filename=self.LOG_FILE,level=logging.DEBUG)
				msg = 'OK'
			except Exception as error:
				msg = 'ERROR : %s' % str(error)
			self.log_msg('Initializing Log File', msg)
    
    ## Initialize Arduino
    def init_arduino(self):        
        if self.ARDUINO_ENABLED:
			try:
				self.arduino = Serial(self.ARDUINO_DEV, self.ARDUINO_BAUD, timeout=self.ARDUINO_TIMEOUT)
				msg = 'OK'
			except Exception as error:
				msg = '\tERROR : %s' % str(error)
			self.log_msg('Initializing Arduino', msg)
    
    ## Initialize Microphone    
    def init_mic(self):
        if self.MICROPHONE_ENABLED:
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
			self.log_msg('Initializing Microphone', msg)
    
    ## Initialize camera
    def init_cam(self):
        if self.CAMERA_ENABLED:
            self.log_msg('Initializing Microphone', 'OK')

    ## Capture Audio
    def capture_audio(self):
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
            result = {
                'db' : rms_decibels,
                'hz' : dominant_hertz,
                }
            msg = 'OKAY: %s' % str(result)
        except Exception as error:
             result = {'microphone_error': str(error)}
             msg = 'ERROR : %s' % str(error)
        self.log_msg('Capturing Audio', msg)
        return result
    
    ## Capture Video
    def capture_video(self):
        try:
            result = {'bees': bees}
            print('\tOKAY: %s' % str(result))
        except Exception as error:
			result = {'camera_error': str(error)}
			print('\tERROR : %s' % str(error))
        self.log_msg('Capturing Video', 'OK')
        return result

    ## Read Arduino
    def read_arduino(self):
        try:
            string = self.arduino.readline()
            result = ast.literal_eval(string)
            msg = 'OK : %s' % str(result)
        except Exception as error:
			result = {'arduino_error' : str(error)}
			msg = 'ERROR : %s' % str(error)
        self.log_msg('Reading Arduino', msg)
        return result
    
    ## Post sample to server
    def post_sample(self, sample):
        try:
            dump = json.dumps(sample)
            req = urllib2.Request(self.WAN_URL)
            req.add_header('Content-Type','application/json')
            response = urllib2.urlopen(req, dump)
            msg = 'OK : %s' % str(response.getcode())
            return response
        except Exception as error:
            msg = 'ERROR : %s' % str(error)
        self.log_msg('Sending to Server', msg)

    ## Send sample to aggregator
    def zmq_sample(self, sample):
        try:
            dump = json.dumps(sample)
            self.socket.send(dump)
            socks = dict(self.poller.poll(self.ZMQ_TIMEOUT))
            if socks:
                if socks.get(self.socket) == zmq.POLLIN:
                    dump = self.socket.recv(zmq.NOBLOCK)
                    response = json.loads(dump)
                    msg = 'OKAY : %s' % str(response)
                    result = response
                else:
                    msg = 'ERROR : Poll Timeout'
                    result = None
            else:
                msg = 'ERROR : Socket Timeout'
        except Exception as error:
            msg = 'ERROR : %s' % str(error)
        self.log_msg('Sending to Aggregator', msg)
        return result
            
    ## Save Data
    def save_sample(self, sample):
        if sample:
            time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            for param in self.PARAMS:
                try:
                    with open('data/' + param + '.csv', 'a') as csv_file:
                        csv_file.write(','.join([time, str(sample[param]), '\n']))
                    print('\tOKAY: ' + param)
                except Exception as error:
                    print('\tERROR: %s' % str(error))
        self.log_msg('Saving Data to File', 'OK')
        
    ## Generate blank sample
    def blank_sample(self):
        sample = {
            'type' : 'sample',
            'fake_time' : datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'),
            'hive_id' : self.HIVE_ID
            }
        self.log_msg('Generating Blank Sample', 'OK')
        return sample
    
    ## Load Config File
    def load_config(self, config):
        self.log_msg('Loading Config File')
        with open(config) as config_file:
            settings = json.loads(config_file.read())
            for key in settings:
                try:
                    getattr(self, key)
                except AttributeError as error:
                    print('\t' + key + ' : ' + str(settings[key]))
                    setattr(self, key, settings[key])
        self.log_msg('Loading Config File', 'OK')
                    
    ## Log Message
    def log_msg(self, task, msg):
        t = datetime.strftime(datetime.now(), "%Y%m%d%H%M%S")
        print('%s [%s] %s' % (t, task, msg))
    
    ## Shutdown
    def shutdown(self):
		self.log_msg('Shutting Down')
		if self.ARDUINO_ENABLED:
			try:
				self.arduino.close()
			except:
				pass
		if self.MICROPHONE_ENABLED:
			try:
				self.microphone.close()
			except:
				pass
		if self.CAMERA_ENABLED:
			try:
				self.camera.release()
			except:
				pass
		if self.REBOOT_ENABLED:
				os.system("sudo reboot")
            
    ## Update to Aggregator
    def update(self):
        print('\n')
        sample = self.blank_sample()
        if self.ARDUINO_ENABLED:
			arduino_result = self.read_arduino()
			sample.update(arduino_result)
        if self.MICROPHONE_ENABLED:
            microphone_result = self.capture_audio()
            sample.update(microphone_result)
        if self.CAMERA_ENABLED:
			camera_result = self.capture_video()
			sample.update(camera_result)
        if self.ZMQ_ENABLED:
			# Try once
			try:
				self.zmq_sample(sample)
			except:
				if self.REBOOT_ENABLED:
					self.shutdown()
        if self.WAN_ENABLED:
            self.post_sample(sample)
        if self.CSV_ENABLED:
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
