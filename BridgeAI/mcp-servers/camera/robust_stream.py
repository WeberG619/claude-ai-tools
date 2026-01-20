#!/usr/bin/env python3
"""
BridgeAI Robust Camera Stream
Captures frames on-demand - more reliable than background thread
"""

import cv2
from flask import Flask, Response
import socket
import time

app = Flask(__name__)

# Global camera instance
camera = None

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

def get_camera():
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for live feed
        time.sleep(0.5)  # Let camera warm up
    return camera

@app.route('/')
def index():
    """Main page with auto-refreshing image"""
    ip = get_local_ip()
    return f'''<!DOCTYPE html>
<html>
<head>
    <title>BridgeAI Camera</title>
    <style>
        * {{ margin: 0; padding: 0; }}
        body {{ background: #000; overflow: hidden; }}
        img {{
            width: 100vw;
            height: 100vh;
            object-fit: contain;
        }}
    </style>
</head>
<body>
    <img id="cam" src="/frame">
    <script>
        var img = document.getElementById('cam');
        function refresh() {{
            img.src = '/frame?' + Date.now();
        }}
        setInterval(refresh, 100);
    </script>
</body>
</html>'''

@app.route('/frame')
def frame():
    """Return current camera frame as JPEG"""
    try:
        cam = get_camera()
        if cam is None or not cam.isOpened():
            return "Camera not available", 503

        # Read frame
        success, img = cam.read()
        if not success or img is None:
            return "Could not capture frame", 503

        # Encode as JPEG
        ret, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            return "Could not encode frame", 500

        return Response(buffer.tobytes(), mimetype='image/jpeg')
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/mjpeg')
def mjpeg():
    """MJPEG stream (alternative method)"""
    def generate():
        while True:
            try:
                cam = get_camera()
                if cam and cam.isOpened():
                    success, img = cam.read()
                    if success and img is not None:
                        ret, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
                        if ret:
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            except:
                pass
            time.sleep(0.033)  # ~30fps

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    ip = get_local_ip()

    print()
    print("=" * 50)
    print("  BridgeAI Camera Stream (Robust)")
    print("=" * 50)
    print(f"  PC Browser:  http://localhost:5001")
    print(f"  TV/Network:  http://{ip}:5001")
    print(f"  MJPEG:       http://{ip}:5001/mjpeg")
    print("=" * 50)
    print()

    # Test camera before starting server
    print("Testing camera...")
    cam = get_camera()
    if cam and cam.isOpened():
        success, _ = cam.read()
        if success:
            print("Camera OK!")
        else:
            print("WARNING: Camera opened but couldn't capture frame")
    else:
        print("WARNING: Could not open camera")

    print("\nStarting server...")
    app.run(host='0.0.0.0', port=5001, threaded=True, debug=False)
