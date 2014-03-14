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
import ast
import json
import os
import sys
import pyaudio
import cherrypy
import numpy as np
import random
from datetime import datetime
from serial import Serial, SerialException
from ctypes import *
from serial import Serial, SerialException
from cherrypy.process.plugins import Monitor
from cherrypy import tools

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
    def __init__(self, config):

        print('[Loading Config File]')
        with open(config) as config_file:
            settings = json.loads(config_file.read())
            print('--> settings : ' + json.dumps(settings, sort_keys=True, indent=4))
            for key in settings:
                try:
                    getattr(self, key)
                except AttributeError as error:
                    setattr(self, key, settings[key])
                    
        print('[Initializing Logs]')
        try:
            for param in ['int_C', 'ext_C', 'int_RH','ext_RH','volts','amps']:
                with open('data/' + param + '.csv', 'w') as csv_file:
                    csv_file.write('date,val,\n') # no spaces!
        except Exception as error:
            print('--> ERROR: ' + str(error))
        
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
            self.arduino = Serial(self.ARDUINO_DEV, self.ARDUINO_BAUD)
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
            sample['hive_id'] = self.HIVE_ID
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
            
    ## Save Data
    def save_data(self, sample):
        print('[Saving Data to File]')
        try:
            time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            for param in ['int_C', 'ext_C', 'int_RH','ext_RH','volts','amps']:
                with open('data/' + param + '.csv', 'a') as csv_file:
                    csv_file.write(','.join([time, str(sample[param]), '\n']))
                
        except Exception as error:
            print('--> ERROR: ' + str(error))
    
    ## Generate random sample
    def random_sample(self):
        print('[Generating Random Sample]')
        sample = {
            'int_C' : random.uniform(0, 50.0),
            'int_RH': random.uniform(0, 100.0),
            'ext_C' : random.uniform(0, 50.0),
            'ext_RH' : random.uniform(0, 100.0),
            'amps' : random.uniform(0, 2.0),
            'volts' : random.uniform(0, 14.2),
            'relay' : random.randint(0,1),
        }
        return sample
        
    ## Display
    def display(self, sample, response):
        print('[Displaying Results]')
        print('--> sample : ' + json.dumps(sample, sort_keys=True, indent=4))
        print('--> response : ' + json.dumps(response, sort_keys=True, indent=4))
    
    ## Shutdown
    def shutdown(self):
        print('[Shutting Down]')
        try:
            self.arduino.close()
            self.microphone.close()
        except Exception as error:
            print('--> ERROR: ' + str(error))
        sys.exit()  
              
    ## Update to Aggregator
    def update(self):
    
        ### Generate empty sample
        print('\n')
        sample = self.random_sample()
        
        ### Read Arduino
        sensors = self.read_arduino()
        if not sensors == None:
            if sensors['relay'] == 1:
                sample.update(sensors)
            else:
                self.shutdown()
        else:
            pass
            
        ### Listen on Mic
        microphone_result = self.capture_audio()
        if not microphone_result == None:
            sample.update(microphone_result) 
    
        ### Try to send sample
        self.send_sample(sample)
        response = self.receive_response()
        self.save_data(sample)
        
        ### Display results
        if self.DEBUG == True:
            self.display(sample, response)
  
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
        '/data': {'tools.staticdir.on':True, 'tools.staticdir.dir':os.path.join(currdir,'data')}, # NEED the '/' before the folder name
        '/js': {'tools.staticdir.on':True, 'tools.staticdir.dir':os.path.join(currdir,'static','js')}, # NEED the '/' before the folder name
    }
    cherrypy.quickstart(node, '/', config=conf)
