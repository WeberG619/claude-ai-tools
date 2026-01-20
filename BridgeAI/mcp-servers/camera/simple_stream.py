#!/usr/bin/env python3
"""
BridgeAI Simple Camera Stream
Uses image refresh method - works on ALL browsers including Samsung TV
"""

import cv2
from flask import Flask, Response, send_file
import io
import time
import socket
import threading

app = Flask(__name__)

# Global frame storage
current_frame = None
camera = None
running = False

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def capture_frames():
    """Continuously capture frames from webcam"""
    global current_frame, camera, running

    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    running = True
    while running:
        success, frame = camera.read()
        if success:
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            current_frame = buffer.tobytes()
        time.sleep(0.033)  # ~30 FPS

    camera.release()

@app.route('/')
def index():
    """Main page - auto-refreshing image"""
    return '''<!DOCTYPE html>
<html>
<head>
    <title>BridgeAI Camera</title>
    <style>
        * { margin: 0; padding: 0; }
        body { background: #000; overflow: hidden; }
        img {
            width: 100vw;
            height: 100vh;
            object-fit: contain;
        }
    </style>
</head>
<body>
    <img id="cam" src="/frame">
    <script>
        // Refresh image every 100ms for smooth video
        var img = document.getElementById('cam');
        setInterval(function() {
            img.src = '/frame?' + new Date().getTime();
        }, 100);
    </script>
</body>
</html>'''

@app.route('/frame')
def frame():
    """Return current camera frame as JPEG"""
    global current_frame
    if current_frame is None:
        # Return a placeholder
        return "Camera starting...", 503

    return Response(current_frame, mimetype='image/jpeg')

@app.route('/video_feed')
def video_feed():
    """MJPEG stream (backup method)"""
    def generate():
        global current_frame
        while True:
            if current_frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + current_frame + b'\r\n')
            time.sleep(0.033)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    ip = get_local_ip()

    print()
    print("="*50)
    print("  BridgeAI Camera Stream (TV Compatible)")
    print("="*50)
    print(f"  Open on TV: http://{ip}:5001")
    print("="*50)
    print()

    # Start frame capture in background
    capture_thread = threading.Thread(target=capture_frames, daemon=True)
    capture_thread.start()

    # Wait for first frame
    time.sleep(1)

    # Run server
    app.run(host='0.0.0.0', port=5001, threaded=True, debug=False)
