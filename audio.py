""" Tuner.py - Takes input from microphone and outputs the average frequency. It then tells the user how close the frequency is to the probable string
on a guitar.

Adapted by Gearoid Moroney from record.py in the pyAudio library and code by Justin Peel from http://stackoverflow.com/questions/2648151/python-frequency-detection"""


import pyaudio
import wave
import numpy as np
import sys
import audioop
#import serial # to communicate with serial port
import time

# def getTuningAdvice(freq, stringFreq):

	# if freq < stringFreq:
		# ser.write('l')
		# time.sleep(0.5)	
		# ser.write('s')
		# return "Tuning Up."
	# elif (stringFreq-(stringFreq*.01)) < freq < (stringFreq+(stringFreq*.01)):
		# ser.write('s')
		# return "OK!"
	# else:
		# ser.write('r')
		# time.sleep(0.5)
		# ser.write('s')
		# return "Tuning Down."

chunk = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 1
WAVE_OUTPUT_FILENAME = "output.wav"

# Lower and Upper Limit for Frequency. Frequencies outside this range will be ignored
LOWER_LIMIT = 200 #40
UPPER_LIMIT = 540

# No sounds below this amplitude will be used
THRESHOLD = 50

# Must have at least MINSAMP frequencies or else the average won't be calculated
MINSAMP = 10

# try:
	# # Set up serial communication
	# ser = serial.Serial()
	# # Set the Serial Port to use
	# #ser.setPort("/dev/ttyUSB0")
	# ser.setPort("/dev/ttyACM0")
	# # Set the Baudrate
	# ser.baudrate = 9600
	# # Open the Serial Connection
	# ser.open()
	# print "Serial port connected!"
# except:
	# print "No serial connection."

while 1==1:

	p = pyaudio.PyAudio()

	try:
		stream = p.open(format = FORMAT,
				channels = CHANNELS,
				rate = RATE,
				input = True,
				frames_per_buffer = chunk)
	except noaudio:
		print "Couldn't get audio!"

	#print "* recording"
	all = []

	for i in range(0, (int) (RATE / chunk * RECORD_SECONDS)):
	    data = stream.read(chunk)
	    all.append(data)
	    
	# print "* done recording"

	stream.stop_stream()
	stream.close()
	p.terminate()

	# write data to WAVE file
	data = ''.join(all)
	wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
	wf.setnchannels(CHANNELS)
	wf.setsampwidth(p.get_sample_size(FORMAT))
	wf.setframerate(RATE)
	wf.writeframes(data)
	wf.close()

	#print "* analysing"

	#chunk = 2048

	fCount = 0 	# the number of frequencies that have been calculated
	fCountWeighted = 0 # fCount weighted by the rms of the frequencies
	sumTotal = 0	# the sum total of all the frequencies

	# open up a wave
	wf = wave.open(WAVE_OUTPUT_FILENAME, 'rb')
	swidth = wf.getsampwidth()
	RATE = wf.getframerate()
	# use a Blackman window
	window = np.blackman(chunk)
	# open stream
	p = pyaudio.PyAudio()
	stream = p.open(format =
		        p.get_format_from_width(wf.getsampwidth()),
		        channels = wf.getnchannels(),
		        rate = RATE,
		        output = True)

	# read some data
	data = wf.readframes(chunk)
	# play stream and find the frequency of each chunk
	while len(data) == chunk*swidth:
	    # write data out to the audio stream
	    # stream.write(data)

	    # unpack the data and times by the hamming window
	    indata = np.array(wave.struct.unpack("%dh"%(len(data)/swidth),\
		                                 data))*window

	    # Take the fft and square each value
	    fftData=abs(np.fft.rfft(indata))**2

	    # find the maximum
	    which = fftData[1:].argmax() + 1

	    # get RMS amplitude
	    rms = audioop.rms(data, 2)

	    # use quadratic interpolation around the max
	    if which != len(fftData)-1:
		y0,y1,y2 = np.log(fftData[which-1:which+2:])
		x1 = (y2 - y0) * .5 / (2 * y1 - y2 - y0)
		# find the frequency and output it
		thefreq = (which+x1)*RATE/chunk

		if((LOWER_LIMIT < thefreq < UPPER_LIMIT) and rms > THRESHOLD):
			sumTotal += (thefreq * rms)
			fCount += 1
			fCountWeighted += rms
			print " *",thefreq
	    else:
		thefreq = which*RATE/chunk
		if((LOWER_LIMIT < thefreq < UPPER_LIMIT) and rms > THRESHOLD):
			sumTotal += thefreq
			fCount += 1
			fCountWeighted += rms
			rms = audioop.rms(data, 2)
			print " *",thefreq,"Hz at",rms,"."

	    # read some more data
	    data = wf.readframes(chunk)
	if data:
	    stream.write(data)
	stream.close()
	p.terminate()

	# Have the frequency, now output data

	# # Set frequency constants
	# LowEString = 82
	# AString = 110
	# DString = 147
	# GString = 196
	# BString = 247
	# HighEString = 330

	# if(fCount > MINSAMP):
		# freq = sumTotal / fCountWeighted

		# #print "Average frequency was", str(freq) + "Hz"

		# if freq < (LowEString + (AString - LowEString)/2): # in the Low E range
			# print "String: Low E. Frequency:",str(freq)+"Hz.",getTuningAdvice(freq, LowEString)
		# elif freq < (AString + (DString - AString)/2):
			# print "String: A",str(freq)+"Hz.",getTuningAdvice(freq, AString)
		# elif freq < (DString + (GString - DString)/2):
			# print "String: D",str(freq)+"Hz.",getTuningAdvice(freq, DString)
		# elif freq < (GString + (BString - GString)/2):
			# print "String: G",str(freq)+"Hz.",getTuningAdvice(freq, GString)
		# elif freq < (BString + (HighEString - BString)/2):
			# print "String: B",str(freq)+"Hz.",getTuningAdvice(freq, BString)
		# else:
			# print "String: High E",str(freq)+"Hz.",getTuningAdvice(freq, HighEString)
	# #else:
		# #print "Frequencies too low."
