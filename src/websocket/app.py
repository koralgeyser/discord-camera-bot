import json
import sys
import os
import time
# import cv2

import numpy as np
import simplejpeg

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import socket
import io
import logging
from http import server
from threading import Condition
from flask import Flask, Response, render_template
from flask_socketio import SocketIO, emit
import constants

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

# class StreamingHandler(server.BaseHTTPRequestHandler):
#     def do_GET(self):
#         if self.path == '/':
#             self.send_response(301)
#             self.send_header('Location', '/index.html')
#             self.end_headers()
#         elif self.path == '/index.html':
#             content = index().encode('utf-8')
#             self.send_response(200)
#             self.send_header('Content-Type', 'text/html')
#             self.send_header('Content-Length', len(content))
#             self.end_headers()
#             self.wfile.write(content)
#         elif self.path == '/stream.mjpg':
#             self.send_response(200)
#             self.send_header('Age', 0)
#             self.send_header('Cache-Control', 'no-cache, private')
#             self.send_header('Pragma', 'no-cache')
#             self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
#             self.end_headers()
#             try:
#                 while True:
#                     with stream_output.condition:
#                         stream_output.condition.wait()
#                         frame = stream_output.frame
#                     self.wfile.write(b'--FRAME\r\n')
#                     self.send_header('Content-Type', 'image/jpeg')
#                     self.send_header('Content-Length', len(frame))
#                     self.end_headers()
#                     self.wfile.write(frame)
#                     self.wfile.write(b'\r\n')
#             except Exception as e:
#                 logging.warning(
#                     'Removed streaming client %s: %s',
#                     self.client_address, str(e))
#         else:
#             self.send_error(404)
#             self.end_headers()


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
        # cameras.camera_instance.
    emit('updateClients', clients, broadcast=True)

@app.route('/')
def index():
    return render_template('index.html',
                           sync_mode=socketio.async_mode)

def gather_img():
    while True:
        # 5 FPS
        time.sleep(0.2)
        # img = np.random.randint(0, 255, size=(600, 1280, 3), dtype=np.uint8)
        with stream_output.condition:
            stream_output.condition.wait()
            frame = stream_output.frame

            # _, frame = cv2.imencode('.jpg', img)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route("/stream.mjpg")
def stream():
    return Response(gather_img(), mimetype='multipart/x-mixed-replace; boundary=frame')

def start(debug=False, use_reloader=False):
    socketio.run(app, host=constants.HOST_NAME, port=constants.PORT, debug=debug, use_reloader=use_reloader)

if __name__ == "__main__":
    import cameras
    start(debug=True, use_reloader=True)
