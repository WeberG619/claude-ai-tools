#!/usr/bin/env python3
"""
Camera diagnostic script - tests if camera is accessible
"""
import cv2
import sys

print("=" * 50)
print("  BridgeAI Camera Diagnostic")
print("=" * 50)

# Try to open camera
print("\nTrying to open camera 0...")
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Could not open camera!")
    print("Possible causes:")
    print("  - Camera is in use by another application")
    print("  - Camera drivers not installed")
    print("  - Camera not connected")
    sys.exit(1)

print("SUCCESS: Camera opened!")

# Get camera info
width = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
height = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
fps = camera.get(cv2.CAP_PROP_FPS)
print(f"Resolution: {int(width)}x{int(height)}")
print(f"FPS: {fps}")

# Try to capture a frame
print("\nCapturing test frame...")
success, frame = camera.read()

if not success or frame is None:
    print("ERROR: Could not capture frame!")
    camera.release()
    sys.exit(1)

print(f"SUCCESS: Captured frame {frame.shape}")

# Save test frame
test_path = r"D:\_CLAUDE-TOOLS\BridgeAI\mcp-servers\camera\test_frame.jpg"
cv2.imwrite(test_path, frame)
print(f"Saved test frame to: {test_path}")

camera.release()
print("\nCamera test PASSED! Camera is working.")
print("=" * 50)
