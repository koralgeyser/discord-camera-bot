import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import io
from threading import Condition
from flask import Flask, Response, render_template
from flask_socketio import SocketIO, emit
import constants
import cameras

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None
app = Flask(__name__)
socketio = SocketIO(app)
clients = 0

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

stream_output = StreamingOutput()

@socketio.on("connect")
def connect():
    global clients, stream_output
    clients += 1
    if clients == 1:
        cameras.camera_instance.start_stream(stream_output)
    emit("updateClients", clients, broadcast=True)

@socketio.on("disconnect")
def disconnect():
    global clients
    clients -= 1
    if clients == 0:
        cameras.camera_instance.stop_stream()
    emit("updateClients", clients, broadcast=True)

@app.route("/")
def index():
    return render_template("index.html", sync_mode=socketio.async_mode)

def gen_frames():
    while True:
        with stream_output.condition:
            stream_output.condition.wait()
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + stream_output.frame + b'\r\n')

@app.route("/stream.mjpg")
def stream():
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

def start(debug=False, use_reloader=False):
    socketio.run(
        app,
        host='0.0.0.0',
        port=constants.PORT,
        debug=debug,
        use_reloader=use_reloader,
    )

if __name__ == "__main__":
    # IMPORTANT: PI Camera does not like this on debug mode
    start(debug=False, use_reloader=True)
