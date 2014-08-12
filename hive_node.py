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
import pyaudio
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
		
        print('[Setting Configuration]')
        self.HIVE_ID = socket.gethostname()
        
        print('[Loading Config File]')
        with open(config) as config_file:
            settings = json.loads(config_file.read())
            for key in settings:
                try:
                    getattr(self, key)
                except AttributeError as error:
                    print('\t' + key + ' : ' + str(settings[key]))
                    setattr(self, key, settings[key])
        
        print('[Initializing Monitor]')
        try:
            Monitor(cherrypy.engine, self.update, frequency=self.CHERRYPY_INTERVAL).subscribe()
            print('\tOKAY')
        except Exception as error:
            print('\tERROR: %s' % str(error))
        
        if self.CSV_ENABLED:      
			print('[Initializing CSV Logs]')
			for param in self.PARAMS:
				try:
					open('data/' + param + '.csv', 'a')
					print('\tUSING EXISTING FILE: ' + param)
				except Exception:
					print('\tCREATING NEW FILE: ' + param)
					with open('data/' + param + '.csv', 'w') as csv_file:
						csv_file.write('date,val,\n') # no spaces!
        
        if self.ZMQ_ENABLED:
			print('[Initializing ZMQ]')
			try:
				self.context = zmq.Context()
				self.socket = self.context.socket(zmq.REQ)
				self.socket.connect(self.ZMQ_SERVER)
				self.poller = zmq.Poller()
				self.poller.register(self.socket, zmq.POLLIN)
				print('\tOKAY')
			except Exception as error:
				print('\tERROR: %s' % str(error))
        
        if self.LOG_ENABLED:
			print('[Initializing Log File]')
			try:
				logging.basicConfig(filename=self.LOG_FILE,level=logging.DEBUG)
			except Exception as error:
				print('\tERROR: %s' % str(error))
            
        if self.ARDUINO_ENABLED:
			print('[Initializing Arduino]')
			try:
				self.arduino = Serial(self.ARDUINO_DEV, self.ARDUINO_BAUD, timeout=self.ARDUINO_TIMEOUT)
				print('\tOKAY')
			except Exception as error:
				print('\tERROR: %s' % str(error))
        
        if self.MICROPHONE_ENABLED:
			print('[Initializing Microphone]')
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
				print('\tOKAY')
			except Exception as error:
				print('\tERROR: %s' % str(error))
            
    ## Capture Audio
    def capture_audio(self):
        print('[Capturing Audio]')
        try:
            self.microphone.start_stream()
            data = self.microphone.read(self.CHUNK)
            wave_array = np.fromstring(data, dtype='int16')
            wave_fft = np.fft.fft(wave_array)
            wave_freqs = np.fft.fftfreq(len(wave_fft))
            frequency = round(self.RATE*abs(wave_freqs[np.argmax(np.abs(wave_fft)**2)]), 1)
            amplitude = np.sqrt(np.mean(np.abs(wave_fft)**2))
            decibels =  round(10*np.log10(amplitude), 1)
            self.microphone.stop_stream()
            result = {'db': decibels, 'hz': frequency}
            print('\tOKAY: %s' % str(result))
        except Exception as error:
			result = {'microphone_error': str(error)}
			print('\tERROR: %s' % str(error))
        return result

    ## Read Arduino
    def read_arduino(self):
        print('[Reading Arduino]')
        try:
            string = self.arduino.readline()
            result = ast.literal_eval(string)
            print('\tOKAY: %s' % str(result))
        except Exception as error:
			result = {'arduino_error' : str(error)}
			print('\tERROR: %s' % str(error))
        return result
    
    ## Post sample to server
    def post_sample(self, sample):
        print('[Sending Sample to Server]')
        try:
            dump = json.dumps(sample)
            req = urllib2.Request(self.WAN_URL)
            req.add_header('Content-Type','application/json')
            response = urllib2.urlopen(req, dump)
            print('\tOKAY: %s' % str(response.getcode()))
            return response
        except Exception as error:
            print('\tERROR: %s' % str(error))

    ## Send sample to aggregator
    def zmq_sample(self, sample):
        print('[Sending Sample to Aggregator]')
        try:
            dump = json.dumps(sample)
            self.socket.send(dump)
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
        except Exception as error:
            print('\tERROR: %s' % str(error))
            raise
            
    ## Save Data
    def save_sample(self, sample):
        print('[Saving Data to File]')
        if sample:
            time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            for param in self.PARAMS:
                try:
                    with open('data/' + param + '.csv', 'a') as csv_file:
                        csv_file.write(','.join([time, str(sample[param]), '\n']))
                    print('\tOKAY: ' + param)
                except Exception as error:
                    print('\tERROR: %s' % str(error))
        
    ## Generate blank sample
    def blank_sample(self):
        print('[Generating Blank Sample]')
        sample = dict(zip(self.PARAMS, [0] * len(self.PARAMS)))
        sample['type'] = 'sample'
        sample['hive_id'] = self.HIVE_ID
        print('\tOKAY')
        return sample
    
    ## Shutdown
    def shutdown(self):
        print('[Shutting Down]')
		if self.ARDUINO_ENABLED:
			self.arduino.close()
		if self.MICROPHONE_ENABLED:
			self.microphone.close()
		if self.CAMERA_ENABLED:
			self.camera.release()
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
			try:
				self.zmq_sample(sample)
			except:
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
