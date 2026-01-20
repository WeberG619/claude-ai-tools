#!/usr/bin/env python3
"""Minimal camera stream - captures on each request"""
import cv2
from flask import Flask, Response
import socket

app = Flask(__name__)

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html><head><title>Camera</title>
<style>*{margin:0}body{background:#000}img{width:100vw;height:100vh;object-fit:contain}</style>
</head><body>
<img id="cam" src="/frame">
<script>setInterval(()=>{document.getElementById('cam').src='/frame?'+Date.now()},150);</script>
</body></html>'''

@app.route('/frame')
def frame():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use DirectShow on Windows
    if not cap.isOpened():
        return 'Camera unavailable', 503
    ret, img = cap.read()
    cap.release()
    if not ret:
        return 'No frame', 503
    _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return Response(buf.tobytes(), mimetype='image/jpeg')

if __name__ == '__main__':
    ip = get_ip()
    print(f"\n=== Camera Stream ===")
    print(f"Browser: http://localhost:5001")
    print(f"Network: http://{ip}:5001\n")
    app.run(host='0.0.0.0', port=5001, threaded=True)
