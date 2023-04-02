import sys
import os
import time
import numpy as np
import simplejpeg
import io
from threading import Condition
from flask import Flask, Response, render_template
from flask_socketio import SocketIO, emit
import constants

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None
app = Flask(__name__)
socketio = SocketIO(app)
clients = 0
capture=None

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

stream_output = StreamingOutput()

@socketio.on('connect')
def connect():
    global clients, stream_output
    clients += 1
    if clients == 1:
        cameras.camera_instance.start_stream(stream_output)
    emit('updateClients', clients, broadcast=True)

@socketio.on('disconnect')
def disconnect():
    global clients
    clients -= 1
    if clients == 0:
        cameras.camera_instance.stop_stream(stream_output)
    emit('updateClients', clients, broadcast=True)

@app.route('/')
def index():
    return render_template('index.html',
                           sync_mode=socketio.async_mode)

def gather_img():
    while True:
        # 5 FPS
        time.sleep(0.2)
        img = np.random.randint(0, 255, size=(600, 1280, 3), dtype=np.uint8)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + simplejpeg.encode_jpeg(img) + b'\r\n')

        # with stream_output.condition:
        #     stream_output.condition.wait()
        #     frame = stream_output.frame
        #     yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + simplejpeg.encode_jpeg(frame) + b'\r\n')

        # rc,img = capture.read()
        # if not rc:
        #     continue
        # imgRGB=cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
        # yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + simplejpeg.encode_jpeg(imgRGB) + b'\r\n')

@app.route("/stream.mjpg")
def stream():
    return Response(gather_img(), mimetype='multipart/x-mixed-replace; boundary=frame')

def start(debug=False, use_reloader=False):
    socketio.run(app, host=constants.HOST_NAME, port=constants.PORT, debug=debug, use_reloader=use_reloader)

if __name__ == "__main__":
    import cameras
    # capture = cv2.VideoCapture(0)
    # capture.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    # capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    # capture.set(cv2.CAP_PROP_SATURATION,0.2)

    start(debug=True, use_reloader=True)
