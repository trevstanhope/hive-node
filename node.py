#!/usr/bin/env python
"""
HiveMind-Plus Node
Developed by Trevor Stanhope
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

# Error Handling
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
def py_error_handler(filename, line, function, err, fmt):
  pass
C_ERROR_HANDLER = ERROR_HANDLER_FUNC(py_error_handler)

# Node
class HiveNode:

  ## Initialize
  def __init__(self):
    print('[Reloading Config File]')
    try:
      self.CONFIG_FILE = sys.argv[1]
    except Exception as error:
      print('--> ' + str(error))
      self.CONFIG_FILE = 'node.conf'
    print('--> ' + self.CONFIG_FILE)
    with open(self.CONFIG_FILE) as config:
      settings = ast.literal_eval(config.read())
      for key in settings:
        try:
          getattr(self, key)
        except AttributeError as error:
          setattr(self, key, settings[key])
    print('[Initializing ZMQ]')
    try:
      self.context = zmq.Context()
      self.socket = self.context.socket(zmq.REQ)
      self.socket.connect(self.ZMQ_SERVER)
      self.poller = zmq.Poller()
      self.poller.register(self.socket, zmq.POLLIN)
    except Exception as error:
      print('--> ' + str(error))
    print('[Initializing Arduino]')
    try:
      self.arduino = serial.Serial(self.ARDUINO_DEV, self.ARDUINO_BAUD, timeout=self.ARDUINO_INTERVAL)
    except Exception as error:
      print('--> ' + str(error))
    self.START_TIME = time.time()
    Monitor(cherrypy.engine, self.update, frequency=self.CHERRYPY_INTERVAL).subscribe()

  ## Update to Aggregator
  def update(self):
    print('\n')
    log = {'time':time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()), 'node':self.NODE_ID}
    print('[Reading Arduino Sensors]')
    try:
      string = self.arduino.read()
      data = ast.literal_eval(string)
      log.update(data)
      print('-->' + str(log))
    except Exception as error:
      print('--> ' + str(error))
    print('[Capturing Audio]')
    try:
      asound = cdll.LoadLibrary('libasound.so')
      asound.snd_lib_error_set_handler(C_ERROR_HANDLER) # Set error handler
      mic = pyaudio.PyAudio()
      stream = mic.open(
        format=self.FORMAT,
        channels=self.CHANNELS,
        rate=self.RATE,
        input=True,
        frames_per_buffer=self.CHUNK
      )
      data = stream.read(self.CHUNK)
      wave_array = np.fromstring(data, dtype='int16')
      wave_fft = np.fft.fft(wave_array)
      wave_freqs = np.fft.fftfreq(len(wave_fft))
      frequency = RATE*abs(wave_freqs[np.argmax(np.abs(wave_fft)**2)])
      amplitude = np.sqrt(np.mean(np.abs(wave_fft)**2))
      decibels =  10*np.log10(amplitude)
      stream.stop_stream()
      log.update({'decibels': decibels, 'frequency': frequency})
    except Exception as error:
      print('--> ' + str(error))
    print('[Sending Message to Aggregator]')
    try:
      dump = json.dumps(log)
      result = self.socket.send(dump)
      for key in log:
        print('--> ' + key + ' : ' + str(log[key]))
    except Exception as error:
      print('--> ' + str(error))
    print('[Receiving Response from Aggregator]')
    try:
      socks = dict(self.poller.poll(self.ZMQ_TIMEOUT))
      if socks:
        if socks.get(self.socket) == zmq.POLLIN:
          dump = self.socket.recv(zmq.NOBLOCK)
          response = json.loads(dump)
          for key in response:
            print('--> ' + key + ' : ' + response[key])
        else:
          print('--> ' + 'Timeout: ' + self.ZMQ_TIMEOUT + 'ms')
      else:
         print('--> ' + 'No messages from Aggregator found')
    except Exception as error:
      print('--> ' + str(error))
  
  ## Render Index
  @cherrypy.expose
  def index(self):
    node = '<p>' + 'node: ' + str(self.NODE_ID) + '</p>'
    start_time = '<p>' + 'Start: ' + time.strftime("%H:%M", time.localtime(self.START_TIME)) + '</p>'
    up_time = '<p>' + 'Up: ' + str(int(time.time() - self.START_TIME)) + '</p>'
    return node + start_time + up_time
    
# Main
if __name__ == '__main__':
  node = HiveNode()
  currdir = os.path.dirname(os.path.abspath(__file__))
  cherrypy.server.socket_host = node.CHERRYPY_ADDR
  cherrypy.server.socket_port = node.CHERRYPY_PORT
 # conf = {'/www': {'tools.staticdir.on':True, 'tools.staticdir.dir':os.path.join(currdir,'www')}}
  cherrypy.quickstart(node, '/')
