#!/usr/bin/env python3
"""
BridgeAI Camera Streaming Server
Streams webcam over HTTP for viewing on any device (including Samsung TV)
"""

import cv2
from flask import Flask, Response, render_template_string
import threading
import socket

app = Flask(__name__)

# Global camera object
camera = None
streaming = False

def get_local_ip():
    """Get the local IP address"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def generate_frames():
    """Generate frames from webcam"""
    global camera, streaming

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use DirectShow on Windows
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    camera.set(cv2.CAP_PROP_FPS, 30)

    streaming = True

    while streaming:
        success, frame = camera.read()
        if not success:
            break

        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_bytes = buffer.tobytes()

        # Yield frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    camera.release()

@app.route('/')
def index():
    """Main page with video stream"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>BridgeAI Camera</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                background: #000;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }
            img {
                max-width: 100%;
                max-height: 100vh;
            }
        </style>
    </head>
    <body>
        <img src="/video_feed" alt="Camera Stream">
    </body>
    </html>
    ''')

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop')
def stop():
    """Stop streaming"""
    global streaming
    streaming = False
    return "Stopped"

def run_server(port=5000):
    """Run the streaming server"""
    ip = get_local_ip()
    print(f"\n{'='*50}")
    print(f"  BridgeAI Camera Stream")
    print(f"{'='*50}")
    print(f"  Local URL:   http://localhost:{port}")
    print(f"  Network URL: http://{ip}:{port}")
    print(f"{'='*50}")
    print(f"  Open this URL on your TV to view the camera")
    print(f"{'='*50}\n")

    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)

if __name__ == '__main__':
    run_server(5000)
