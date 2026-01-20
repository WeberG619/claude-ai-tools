import argparse
import json
import logging
import sys
import time
import win32pipe
import win32file
import pywintypes
from src.realtime_stt import RealtimeSTT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IPCServer:
    def __init__(self, pipe_name):
        self.pipe_name = f"\\\\.\\pipe\\{pipe_name}"
        self.pipe = None
        self.stt = None
        self.running = False
        
    def start(self):
        self.pipe = win32pipe.CreateNamedPipe(
            self.pipe_name,
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
            1, 65536, 65536, 0, None
        )
        
        logger.info(f"Waiting for connection on {self.pipe_name}")
        win32pipe.ConnectNamedPipe(self.pipe, None)
        logger.info("Client connected")
        
        self.stt = RealtimeSTT(
            model_size="base",
            device="cpu",
            language="en",
            wake_word="claude",
            use_wake_word=True,
            vad_enabled=True,
            on_transcription=self.on_transcription,
            on_wake_word=self.on_wake_word,
            on_start_recording=self.on_start_recording,
            on_stop_recording=self.on_stop_recording
        )
        
        self.stt.start()
        self.running = True
        
        self.process_commands()
        
    def send_message(self, message_type, data):
        try:
            message = {"type": message_type, "data": data}
            json_str = json.dumps(message)
            win32file.WriteFile(self.pipe, json_str.encode())
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            
    def on_transcription(self, text):
        self.send_message("transcription", {
            "text": text,
            "timestamp": time.time()
        })
        
    def on_wake_word(self):
        self.send_message("wake_word", {
            "wake_word": "claude",
            "timestamp": time.time()
        })
        
    def on_start_recording(self):
        self.send_message("recording_started", {})
        
    def on_stop_recording(self):
        self.send_message("recording_stopped", {})
        
    def process_commands(self):
        while self.running:
            try:
                result, data = win32file.ReadFile(self.pipe, 64*1024)
                if result == 0:
                    message = json.loads(data.decode())
                    self.handle_command(message)
            except pywintypes.error as e:
                if e.args[0] == 109:
                    logger.info("Pipe closed by client")
                    break
                else:
                    logger.error(f"Pipe error: {e}")
            except Exception as e:
                logger.error(f"Error processing command: {e}")
                
    def handle_command(self, message):
        if message.get("type") == "command":
            command = message.get("data", "").upper()
            if command == "STOP":
                self.running = False
                self.stt.stop()
                
    def stop(self):
        self.running = False
        if self.stt:
            self.stt.stop()
        if self.pipe:
            win32pipe.DisconnectNamedPipe(self.pipe)
            win32file.CloseHandle(self.pipe)

def main():
    parser = argparse.ArgumentParser(description="Claude STT IPC Server")
    parser.add_argument("--pipe-name", required=True, help="Named pipe name for IPC")
    args = parser.parse_args()
    
    server = IPCServer(args.pipe_name)
    
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        server.stop()
        
if __name__ == "__main__":
    main()