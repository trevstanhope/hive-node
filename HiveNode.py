#!/usr/bin/env python
"""
HiveMind Node
Developed by Trevor Stanhope
Hive sensor node based on RaspberryPi and Arduino.

TODO:
- Authenticate to aggregator?
- Set environment variables/keys by JSON
- Validate data received from Arduino
"""

# Libraries
import zmq
import serial
from serial import SerialException
import ast
import json
import time
import os
import sys
import pyaudio
from ctypes import *
import cherrypy
from cherrypy.process.plugins import Monitor
from cherrypy import tools
import os
import numpy as np
import random

# Constants
try:
    CONFIG_FILE = sys.argv[1]
except Exception as err:
    CONFIG_FILE = 'settings.json'

# Error Handling
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
def py_error_handler(filename, line, function, err, fmt):
  pass
C_ERROR_HANDLER = ERROR_HANDLER_FUNC(py_error_handler)

# Node
class HiveNode:

  ## Initialize
    def __init__(self):

        print('[Loading Config File]')
        with open(CONFIG_FILE) as config_file:
            settings = ast.literal_eval(config_file.read())
            for key in settings:
                try:
                    getattr(self, key)
                except AttributeError as error:
                    print(key + ' : ' + str(settings[key]))
                    setattr(self, key, settings[key])

        print('[Initializing ZMQ]')
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(self.ZMQ_SERVER)
            self.poller = zmq.Poller()
            self.poller.register(self.socket, zmq.POLLIN)
        except Exception as error:
            print('--> ERROR: ' + str(error))

        print('[Initializing Arduino]')
        try:
            self.arduino = serial.Serial(self.ARDUINO_DEV, self.ARDUINO_BAUD)
        except Exception as error:
            print('--> ERROR: ' + str(error))

        print('[Initializing Monitor]')
        Monitor(cherrypy.engine, self.update, frequency=self.CHERRYPY_INTERVAL).subscribe()

        print('[Initializing Microphone]')
        try:
            asound = cdll.LoadLibrary('libasound.so')
            asound.snd_lib_error_set_handler(C_ERROR_HANDLER) # Set error handler
            mic = pyaudio.PyAudio()
            self.microphone = mic.open(
	            format=self.FORMAT,
	            channels=self.CHANNELS,
	            rate=self.RATE,
	            input=True,
	            frames_per_buffer=self.CHUNK
            )
            self.microphone.stop_stream()
        except Exception as error:
            print('--> ERROR: ' + str(error))

    ## Capture Audio
    def capture_audio(self):
        print('[Capturing Audio]')
        try:
            self.microphone.start_stream()
            data = self.microphone.read(self.CHUNK)
            wave_array = np.fromstring(data, dtype='int16')
            wave_fft = np.fft.fft(wave_array)
            wave_freqs = np.fft.fftfreq(len(wave_fft))
            frequency = self.RATE*abs(wave_freqs[np.argmax(np.abs(wave_fft)**2)])
            amplitude = np.sqrt(np.mean(np.abs(wave_fft)**2))
            decibels =  10*np.log10(amplitude)
            self.microphone.stop_stream()
            result = {'decibels': decibels, 'frequency': frequency}
            return result
        except Exception as error:
            print('--> ERROR: ' + str(error))
            return None

    ## Read Arduino
    def read_arduino(self):
        print('[Reading Arduino]')
        try:
            string = self.arduino.readline()
            result = ast.literal_eval(string)
            return result
        except Exception as error:
            print('--> ERROR: ' + str(error))
            return None

    ## Send sample to aggregator
    def send_sample(self, sample):
        print('[Sending Sample]')
        try:
            dump = json.dumps(sample)
            result = self.socket.send(dump)
            return result
        except Exception as error:
            print('--> ERROR: ' + str(error))
            return None
    
    ## Receive response from aggregator
    def receive_response(self):
        print('[Receiving Response]')
        try:
            socks = dict(self.poller.poll(self.ZMQ_TIMEOUT))
            if socks:
                if socks.get(self.socket) == zmq.POLLIN:
                    dump = self.socket.recv(zmq.NOBLOCK)
                    response = json.loads(dump)
                    return response
                else:
                    return None
            else:
                return None
        except Exception as error:
            print('--> ERROR: ' + str(error))
            return None

    ## Update to Aggregator
    def update(self):
        print('\n')
        sample = {
            'hive_id':self.HIVE_ID
        }
        sample['temperature'] = random.randint(0,100) #RANDOM
        sample['humidity'] = random.randint(0,100) #RANDOM
        arduino_result = self.read_arduino()
        if not arduino_result == None:
            sample.update(arduino_result)
        microphone_result = self.capture_audio()
        if not microphone_result == None:
            sample.update(microphone_result)
        self.send_sample(sample)
        self.receive_response()
  
    ## Render Index
    @cherrypy.expose
    def index(self):
        html = open('static/index.html').read()
        return html
    
# Main
if __name__ == '__main__':
    node = HiveNode()
    currdir = os.path.dirname(os.path.abspath(__file__))
    cherrypy.server.socket_host = node.CHERRYPY_ADDR
    cherrypy.server.socket_port = node.CHERRYPY_PORT
    conf = {
        '/static': {'tools.staticdir.on':True, 'tools.staticdir.dir':os.path.join(currdir,'static')}
    }
    cherrypy.quickstart(node, '/', config=conf)
