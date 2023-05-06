import io
import sys
from threading import Thread
import time
from typing import Any, Final
import numpy as np
from abc import ABC, abstractmethod
import simplejpeg
from PIL import Image

if sys.platform.startswith("linux"):
    import picamera2
    from picamera2.picamera2 import Picamera2
    from picamera2.encoders.mjpeg_encoder import MJPEGEncoder
    from picamera2.outputs import FileOutput

class Camera(ABC):
    dtype: str
    shape: Any
    name: str

    @abstractmethod
    def set_params(self, params):
        pass

    @abstractmethod
    def snap(self) -> Image.Image:
        pass

    @abstractmethod
    def start_stream(self, output):
        pass

    @abstractmethod
    def stop_stream(self):
        pass

    @property
    def metadata(self):
        return dict(name=self.__str__(), dtype=str(self.dtype), shape=self.shape)


class RPiCamera(Camera):
    def __init__(self):
        self.picam2 = Picamera2()
        # https://www.raspberrypi.com/documentation/accessories/camera.html
        # 4.2.1.6. More on the encode stream
        # Still images from main stream
        # Video stream from lores stream
        res = self.picam2.sensor_resolution
        self.shape = (int(res[0]/2), int(res[1]/2))
        video_config = self.picam2.create_video_configuration(
            main={"size": self.shape},
            lores={"size": (int(self.shape[0]/5), int(self.shape[1]/5))},
            encode="lores",
            # 10 FPS
            controls={"FrameDurationLimits": (100000, 100000)},
        )
        self.picam2.configure(video_config)
        self.picam2.start()

        # Give time for Aec and Awb to settle, before disabling them
        time.sleep(1)
        self.picam2.set_controls({"AeEnable": False, "AwbEnable": False, "FrameRate": 1.0})
        # And wait for those settings to take effect
        time.sleep(1)


        self.dtype = "uint8"
        self.gain = 1.0
        self.exposure = 10000  # us

    def __str__(self) -> str:
        return "Raspberry Pi Camera"

    def start_stream(self, output):
        self.picam2.start_encoder(MJPEGEncoder(), FileOutput(output))

    def stop_stream(self):
        self.picam2.stop_encoder()

    def snap(self):
        request: picamera2.picamera2.CompletedRequest = self.picam2.capture_request()
        # snap: np.ndarray = request.make_array("main")
        snap: Image.Image = request.make_image("main")
        request.release()
        return snap

    def set_params(self, params):
        msg = []
        if "name" in params:
            newname = str(params["name"])
            msg.append("name: %s > %s" % (self.name, newname))
            self.name = newname
        if "width" in params:
            newwidth = int(params["width"])
            msg.append("width: %d > %d" % (self.shape[0], newwidth))
            self.shape[0] = newwidth
        if "height" in params:
            newheight = int(params["height"])
            msg.append("height: %d > %d" % (self.shape[1], newheight))
            self.shape[1] = newheight
        if "exposure" in params:
            newexposure = int(params["exposure"])
            msg.append("exposure: %d > %d" % (self.exposure, newexposure))
            self.exposure = newexposure
        if "gain" in params:
            newgain = float(params["gain"])
            msg.append("gain: %d > %d" % (self.gain, newgain))
            self.gain = newgain
        self.picam2.stop()
        capture_config = self.picam2.still_configuration(
            main={"size": (self.shape[1], self.shape[0]), "format": "BGR888"}
        )
        self.picam2.configure(capture_config)
        self.picam2.start({"ExposureTime": self.exposure, "AnalogueGain": self.gain})
        return "\n".join(msg)


class DummyCamera(Camera):
    def __init__(self):
        self.shape = (64, 64)
        self.dtype = "uint16"
        with open("data/sample_snap.npy", mode="rb") as fs:
            p = fs.read()
        self.parappa = (
            np.frombuffer(p, dtype="uint8").reshape(self.shape).astype("double") / 255.0
        )
        self.exposure = 50.0

    def __str__(self) -> str:
        return "Dummy Camera"

    def snap(self):
        snap = np.random.poisson(
            (self.parappa * 10.0 + 1.0) * self.exposure
        ).astype("uint16")
        return Image.fromarray(np.uint8(snap))

    def start_stream(self, output: io.BufferedIOBase):
        self.is_streaming = True
        def stream():
            while True:
                # 5 FPS
                time.sleep(0.2)
                if not self.is_streaming:
                    break
                
                output.write(
                    simplejpeg.encode_jpeg(np.random.randint(0, 255, size=(600, 1280, 3), dtype=np.uint8))
                )

        self.worker = Thread(target=stream)
        self.worker.start()

    def stop_stream(self,):
        self.is_streaming = False
        self.worker.join()

    def set_params(self, params):
        msg = []
        if "exposure" in params:
            newexposure = float(params["exposure"])
            msg.append("exposure: %f > %f" % (self.exposure, newexposure))
            self.exposure = newexposure
        if "name" in params:
            newname = str(params["name"])
            msg.append("name: %s > %s" % (self.name, newname))
            self.name = newname
        return "\n".join(msg)


def _setup_camera() -> Camera:
    """Statically called at run time"""
    if sys.platform.startswith("linux"):
        try:
            return RPiCamera()
        except:
            return DummyCamera()
    else:
        return DummyCamera()


camera_instance: Final[Camera] = _setup_camera()

if __name__=='__main__':
	import matplotlib.pyplot as plt
	snap = camera_instance.snap()
	plt.imshow(snap)
	plt.show()
