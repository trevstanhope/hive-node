#!/usr/bin/env python
"""
HiveMind Node
Developed by Trevor Stanhope
Hive sensor node based on RaspberryPi and Arduino.

TODO:
- Authenticate to aggregator?
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
            print('\tsettings : ' + json.dumps(settings, sort_keys=True, indent=4))
            for key in settings:
                try:
                    getattr(self, key)
                except AttributeError as error:
                    setattr(self, key, settings[key])
                    
        print('[Initializing CSV Logs]')
        try:
            for param in self.PARAMS:
                with open('data/' + param + '.csv', 'w') as csv_file:
                    csv_file.write('date,val,\n') # no spaces!
            print('\tOKAY')
        except Exception as error:
            print('\t ERROR: ' + str(error))
        
        print('[Initializing ZMQ]')
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(self.ZMQ_SERVER)
            self.poller = zmq.Poller()
            self.poller.register(self.socket, zmq.POLLIN)
            print('\tOKAY')
        except Exception as error:
            print('\tERROR: ' + str(error))

        print('[Initializing Arduino]')
        try:
            self.arduino = Serial(self.ARDUINO_DEV, self.ARDUINO_BAUD)
            print('\tOKAY')
        except Exception as error:
            print('\tERROR: ' + str(error))

        print('[Initializing Monitor]')
        try:
            Monitor(cherrypy.engine, self.update, frequency=self.CHERRYPY_INTERVAL).subscribe()
            print('\tOKAY')
        except Exception as error:
            print('\tERROR: ' + str(error))
            
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
            print('\tOKAY')
        except Exception as error:
            print('\tERROR: ' + str(error))

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
            result = {'db': decibels, 'hz': frequency}
            print('\t' + str(result))
            return result
        except Exception as error:
            print('\tERROR: ' + str(error))
            return None

    ## Read Arduino
    def read_arduino(self):
        print('[Reading Arduino]')
        try:
            string = self.arduino.readline()
            result = ast.literal_eval(string)
            print('\t' + str(result))
            return result
        except Exception as error:
            print('\tERROR: ' + str(error))
            return None

    ## Send sample to aggregator
    def send_sample(self, sample):
        print('[Sending Sample]')
        try:
            dump = json.dumps(sample, indent=4)
            self.socket.send(dump)
            print(dump)
            return True
        except Exception as error:
            print('\tERROR: ' + str(error))
            return False
    
    ## Receive response from aggregator
    def receive_response(self):
        print('[Receiving Response]')
        try:
            socks = dict(self.poller.poll(self.ZMQ_TIMEOUT))
            if socks:
                if socks.get(self.socket) == zmq.POLLIN:
                    dump = self.socket.recv(zmq.NOBLOCK)
                    response = json.loads(dump)
                    print('\tOKAY: ' + str(response))
                    return response
                else:
                    print('\tERROR: Poll Timeout')
                    return None
            else:
                print('\tERROR: Socket Timeout')
                return None
        except Exception as error:
            print('\tERROR: ' + str(error))
            return None
            
    ## Save Data
    def save_data(self, sample):
        print('[Saving Data to File]')
        if sample:
            time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            for param in self.PARAMS:
                try:
                    with open('data/' + param + '.csv', 'a') as csv_file:
                        csv_file.write(','.join([time, str(sample[param]), '\n']))
                    print('\tOKAY: ' + param)
                except Exception as error:
                    print('\tERROR: ' + str(error)) 
        
    ## Generate blank sample
    def blank_sample(self):
        print('[Generating BLANK Sample]')
        sample = {
            'type' : 'sample',
            'hive_id' : self.HIVE_ID
        }
        return sample
    
    ## Generate random sample
    def random_sample(self):
        print('[Generating RANDOM Sample]')
        sample = {
            'type' : 'sample',
            'hive_id' : self.HIVE_ID,
            'int_t' : random.randint(0,35),
            'ext_t' : random.randint(0,35),
            'int_h' : random.randint(0,100),
            'ext_h' : random.randint(0,100),
            'volts' : random.randint(0,15),
            'amps'  : random.randint(0,2),
            'db'    : random.randint(0,200),
            'hz'    : random.randint(0,4000),
        }
        return sample
    
    ## Shutdown
    def shutdown(self):
        print('[Shutting Down]')
        try:
            self.arduino.close()
            self.microphone.close()
            sys.exit() 
        except Exception as error:
            print('\tERROR: ' + str(error))
            
    ## Update to Aggregator
    def update(self):
        print('\n')
        if self.DEBUG:
            sample = self.random_sample()
        else: 
            sample = self.blank_sample()
            sensors = self.read_arduino()
            if not sensors == None:
                sample.update(sensors)
            microphone_result = self.capture_audio()
            if not microphone_result == None:
                sample.update(microphone_result) 
        self.send_sample(sample)
        response = self.receive_response()
        self.save_data(sample)

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
#    cherrypy.config.update({ "environment": "embedded" })
    conf = {
        '/': {'tools.staticdir.on':True, 'tools.staticdir.dir':os.path.join(currdir,'static')},
        '/data': {'tools.staticdir.on':True, 'tools.staticdir.dir':os.path.join(currdir,'data')}, # NEED the '/' before the folder name
        '/js': {'tools.staticdir.on':True, 'tools.staticdir.dir':os.path.join(currdir,'static','js')}, # NEED the '/' before the folder name
    }
    cherrypy.quickstart(node, '/', config=conf)
