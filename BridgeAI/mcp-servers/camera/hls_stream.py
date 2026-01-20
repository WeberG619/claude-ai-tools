#!/usr/bin/env python3
"""
BridgeAI HLS Camera Stream
Creates TV-compatible video stream using HLS format
"""

import subprocess
import os
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket

STREAM_DIR = r"D:\_CLAUDE-TOOLS\BridgeAI\mcp-servers\camera\stream"
PORT = 8080

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def start_ffmpeg_stream():
    """Start FFmpeg to capture webcam and create HLS stream"""

    # Create stream directory
    os.makedirs(STREAM_DIR, exist_ok=True)

    # FFmpeg command to capture webcam and output HLS
    # Using DirectShow for Windows webcam capture
    cmd = [
        'ffmpeg',
        '-f', 'dshow',                          # DirectShow (Windows)
        '-i', 'video=HD Pro Webcam C920',       # Your webcam
        '-c:v', 'libx264',                      # H.264 codec (TV compatible)
        '-preset', 'ultrafast',                 # Fast encoding
        '-tune', 'zerolatency',                 # Low latency
        '-g', '30',                             # Keyframe every 30 frames
        '-sc_threshold', '0',
        '-f', 'hls',                            # HLS output format
        '-hls_time', '2',                       # 2 second segments
        '-hls_list_size', '3',                  # Keep 3 segments
        '-hls_flags', 'delete_segments',        # Clean up old segments
        '-hls_segment_filename', os.path.join(STREAM_DIR, 'segment_%03d.ts'),
        os.path.join(STREAM_DIR, 'stream.m3u8')
    ]

    print("Starting FFmpeg webcam capture...")
    print(f"Command: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )

    return process

class CORSRequestHandler(SimpleHTTPRequestHandler):
    """HTTP handler with CORS headers for TV access"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STREAM_DIR, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

def start_http_server():
    """Start HTTP server to serve HLS stream"""
    server = HTTPServer(('0.0.0.0', PORT), CORSRequestHandler)
    print(f"HTTP server running on port {PORT}")
    server.serve_forever()

if __name__ == '__main__':
    ip = get_local_ip()

    print("="*50)
    print("  BridgeAI HLS Camera Stream")
    print("="*50)
    print(f"  Stream URL: http://{ip}:{PORT}/stream.m3u8")
    print("="*50)
    print()

    # Start HTTP server in background thread
    server_thread = threading.Thread(target=start_http_server, daemon=True)
    server_thread.start()

    # Give server time to start
    time.sleep(1)

    # Start FFmpeg streaming
    ffmpeg = start_ffmpeg_stream()

    print("\nStreaming... Press Ctrl+C to stop")

    try:
        ffmpeg.wait()
    except KeyboardInterrupt:
        ffmpeg.terminate()
        print("\nStream stopped.")
