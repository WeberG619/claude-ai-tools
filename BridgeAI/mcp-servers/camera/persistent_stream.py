#!/usr/bin/env python3
"""
BridgeAI Camera Stream - Persistent camera connection
Keeps camera open for fast frame serving
"""
import cv2
from flask import Flask, Response
import socket
import threading
import time

app = Flask(__name__)

# Global camera and frame
camera = None
current_frame = None
frame_lock = threading.Lock()

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

def camera_thread():
    """Background thread that continuously captures frames"""
    global camera, current_frame

    print("Opening camera with DirectShow...")
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not camera.isOpened():
        print("ERROR: Could not open camera!")
        return

    print("Camera opened successfully!")

    while True:
        ret, frame = camera.read()
        if ret and frame is not None:
            # Encode to JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            with frame_lock:
                current_frame = buffer.tobytes()
        time.sleep(0.033)  # ~30 FPS

@app.route('/')
def index():
    ip = get_ip()
    return f'''<!DOCTYPE html>
<html>
<head>
    <title>BridgeAI Camera</title>
    <style>
        * {{ margin: 0; padding: 0; }}
        body {{ background: #000; overflow: hidden; }}
        img {{ width: 100vw; height: 100vh; object-fit: contain; }}
    </style>
</head>
<body>
    <img id="cam" src="/frame">
    <script>
        var img = document.getElementById('cam');
        setInterval(function() {{
            img.src = '/frame?' + Date.now();
        }}, 100);
    </script>
</body>
</html>'''

@app.route('/frame')
def frame():
    global current_frame
    with frame_lock:
        if current_frame is None:
            return 'Camera starting...', 503
        return Response(current_frame, mimetype='image/jpeg')

@app.route('/mjpeg')
def mjpeg():
    """MJPEG stream for browsers that support it"""
    def generate():
        global current_frame
        while True:
            with frame_lock:
                if current_frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + current_frame + b'\r\n')
            time.sleep(0.033)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    ip = get_ip()

    print()
    print("=" * 50)
    print("  BridgeAI Camera Stream")
    print("=" * 50)
    print(f"  PC:  http://localhost:5001")
    print(f"  TV:  http://{ip}:5001")
    print("=" * 50)
    print()

    # Start camera thread
    cam_thread = threading.Thread(target=camera_thread, daemon=True)
    cam_thread.start()

    # Wait for camera to initialize
    print("Waiting for camera to initialize...")
    time.sleep(3)

    if current_frame:
        print(f"Camera ready! Frame size: {len(current_frame)} bytes")
    else:
        print("WARNING: No frames captured yet")

    print("\nStarting web server...")
    app.run(host='0.0.0.0', port=5001, threaded=True, debug=False)
