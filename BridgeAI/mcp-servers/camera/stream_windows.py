#!/usr/bin/env python3
"""
BridgeAI Camera Stream Server - Windows Version
Run this directly on Windows (not WSL) for network access
"""

import cv2
from flask import Flask, Response, render_template_string
import socket

app = Flask(__name__)

def get_local_ip():
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
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    while True:
        success, frame = camera.read()
        if not success:
            break
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index():
    return '''<!DOCTYPE html>
    <html><head><title>BridgeAI Camera</title>
    <style>body{margin:0;background:#000;display:flex;justify-content:center;align-items:center;min-height:100vh}
    img{max-width:100%;max-height:100vh}</style></head>
    <body><img src="/video_feed"></body></html>'''

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    ip = get_local_ip()
    print(f"\n{'='*50}")
    print(f"  BridgeAI Camera Stream")
    print(f"  Open on TV: http://{ip}:5000")
    print(f"{'='*50}\n")
    app.run(host='0.0.0.0', port=5000, threaded=True)
