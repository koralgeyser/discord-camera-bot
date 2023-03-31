import io
import re
import subprocess
import sys
from typing import Any, Final
import numpy as np
from abc import ABC, abstractmethod

if sys.platform.startswith("linux"):
	import picamera2
	from picamera2.picamera2 import Picamera2
	from picamera2.configuration import CameraConfiguration
	from picamera2.encoders.mjpeg_encoder import MJPEGEncoder
	from picamera2.outputs import FileOutput, FfmpegOutput
	
class Camera(ABC):
	dtype: str
	shape: Any
	name: str
	@abstractmethod
	def set_params(self, params):
		pass

	@abstractmethod
	def snap(self):
		pass

	@abstractmethod
	def start_stream(self, output):
		pass

	@abstractmethod
	def stop_stream(self):
		pass

	@property
	def metadata(self):
		return dict(name=self.name,dtype=str(self.dtype),shape=self.shape)
			
class RPiCamera(Camera):
	def __init__(self):
		self.picam2 = Picamera2()
		# https://www.raspberrypi.com/documentation/accessories/camera.html
		# 4.2.1.6. More on the encode stream
		# Still images from main stream 
		# Video stream from lores stream
		res = self.picam2.sensor_resolution
		video_config = self.picam2.create_video_configuration(
			main={
				"size": (int(res[0]/1.5), int(res[1]/1.5))
			},
			lores={
				"size": (1332, 990)
			},
			encode="lores",
			# 10 FPS
			controls={
				"FrameDurationLimits": (100000, 100000)
			}
		)
		self.picam2.configure(video_config)
		self.picam2.start()

		self.dtype = 'uint8'
		self.gain = 1.0
		self.exposure = 10000 #us
		self.name = 'libcamera raspberry pi cam'
		# self.set_params({})
		self.last = None

	def __del__(self):
		self.picam2.close()
		del(self)

	def __str__(self) -> str:
		return "Raspberry Pi Camera"

	def start_stream(self, output):
		self.picam2.start_encoder(MJPEGEncoder(), FileOutput(output))

	def stop_stream(self):
		pass

	def snap(self):
		from PIL import Image
	    
		request: picamera2.picamera2.CompletedRequest = self.picam2.capture_request()
		snap: np.ndarray = request.make_array("main")
		request.release()
		# Add logging here
		# try:
		# except:
		# 	snap = np.zeros(self.picam2.sensor_resolution,dtype=self.dtype)
		return snap


	def set_params(self,params):
		msg = []
		if 'name' in params:
			newname = str(params['name'])
			msg.append('name: %s > %s'%(self.name,newname))
			self.name = newname
		if 'width' in params:
			newwidth = int(params['width'])
			msg.append('width: %d > %d'%(self.shape[0],newwidth))
			self.shape[0] = newwidth
		if 'height' in params:
			newheight = int(params['height'])
			msg.append('height: %d > %d'%(self.shape[1],newheight))
			self.shape[1] = newheight
		if 'exposure' in params:
			newexposure = int(params['exposure'])
			msg.append('exposure: %d > %d'%(self.exposure,newexposure))
			self.exposure = newexposure
		if 'gain' in params:
			newgain = float(params['gain'])
			msg.append('gain: %d > %d'%(self.gain,newgain))
			self.gain = newgain
		self.picam2.stop()
		capture_config = self.picam2.still_configuration(main = {"size" : (self.shape[1], self.shape[0]), "format" : "BGR888"})
		self.picam2.configure(capture_config)
		self.picam2.start({"ExposureTime":self.exposure,"AnalogueGain":self.gain})
		return '\n'.join(msg)
	
class DummyCamera(Camera):
	def __init__(self):
		self.shape = (64,64)
		self.dtype = 'uint16'
		with open("data/sample_snap.npy", mode="rb") as fs:
			p = fs.read()
		self.parappa = np.frombuffer(p,dtype='uint8').reshape((64,64)).astype('double')/255.
		self.exposure = 50.
		self.name = 'parappa cam'
		self.last = None
		self.snap()

	def __str__(self) -> str:
		return "Dummy Camera"

	def snap(self):
		self.last = np.random.poisson((self.parappa*10.+1.)*self.exposure).astype('uint16')
		return self.last

	def start_stream(self, output):
		pass

	def stop_stream(self):
		pass

	def set_params(self,params):
		msg = []
		if 'exposure' in params:
			newexposure = float(params['exposure'])
			msg.append('exposure: %f > %f'%(self.exposure,newexposure))
			self.exposure = newexposure
		if 'name' in params:
			newname = str(params['name'])
			msg.append('name: %s > %s'%(self.name,newname))
			self.name = newname
		return '\n'.join(msg)

def _setup_camera() -> Camera:
	"""'Statically' called during run time"""
	if sys.platform.startswith("linux"):
		try:
			return RPiCamera()
		except:
			return DummyCamera()
	else:
		return DummyCamera()

camera_instance: Final[Camera] = _setup_camera()

# if __name__=='__main__':
# 	# live_stream()
# 	import matplotlib.pyplot as plt
# 	snap = camera_instance.snap()
# 	plt.imshow(snap)
# 	plt.show()
