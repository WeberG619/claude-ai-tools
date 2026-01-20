import numpy as np
import time
import logging
from typing import Callable, Optional, Dict, Any
from colorama import Fore, Style, init
import threading
import queue

try:
    from .audio_recorder import AudioRecorder
except ImportError:
    from .audio_recorder_simple import AudioRecorder
    
try:
    from .vad import VoiceActivityDetector
except ImportError:
    from .vad_simple import VoiceActivityDetector
    
from .wake_word import SimpleWakeWordDetector, WakeWordDetector
from .transcriber import Transcriber

init(autoreset=True)
logger = logging.getLogger(__name__)

class RealtimeSTT:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "en",
        wake_word: str = "claude",
        use_wake_word: bool = True,
        vad_enabled: bool = True,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        on_transcription: Optional[Callable[[str], None]] = None,
        on_wake_word: Optional[Callable[[], None]] = None,
        on_start_recording: Optional[Callable[[], None]] = None,
        on_stop_recording: Optional[Callable[[], None]] = None
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.use_wake_word = use_wake_word
        self.vad_enabled = vad_enabled
        self.wake_word = wake_word
        
        self.on_transcription = on_transcription
        self.on_wake_word = on_wake_word
        self.on_start_recording = on_start_recording
        self.on_stop_recording = on_stop_recording
        
        self.audio_recorder = AudioRecorder(
            sample_rate=sample_rate,
            chunk_size=chunk_size
        )
        
        if vad_enabled:
            self.vad = VoiceActivityDetector(
                sample_rate=sample_rate,
                frame_duration_ms=30,
                use_silero=True
            )
        else:
            self.vad = None
            
        if use_wake_word:
            self.wake_detector = SimpleWakeWordDetector(
                wake_word=wake_word,
                sample_rate=sample_rate
            )
            try:
                self.porcupine_detector = WakeWordDetector(
                    wake_words=[wake_word],
                    sensitivities=[0.5]
                )
                # Disable if Porcupine didn't initialize properly
                if not self.porcupine_detector.porcupine:
                    self.porcupine_detector = None
            except Exception as e:
                logger.warning(f"Could not initialize Porcupine detector: {e}")
                self.porcupine_detector = None
        else:
            self.wake_detector = None
            self.porcupine_detector = None
            
        self.transcriber = Transcriber(
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            language=language,
            vad_filter=True
        )
        
        self.is_running = False
        self.is_activated = not use_wake_word
        self.is_recording = False
        self.audio_buffer = []
        self.silence_start = None
        self.max_silence_duration = 2.0
        
        self._processing_thread = None
        self._transcription_queue = queue.Queue()
        
    def start(self):
        if self.is_running:
            return
            
        self.is_running = True
        
        self.transcriber.start(callback=self._on_transcription)
        
        self.audio_recorder.start_recording(callback=self._process_audio_chunk)
        
        self._processing_thread = threading.Thread(target=self._process_transcriptions)
        self._processing_thread.daemon = True
        self._processing_thread.start()
        
        logger.info("RealtimeSTT started")
        
        if self.use_wake_word:
            print(f"{Fore.CYAN}Listening for wake word '{self.wake_word}'...{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}Ready for speech input...{Style.RESET_ALL}")
            
    def stop(self):
        if not self.is_running:
            return
            
        self.is_running = False
        
        self.audio_recorder.stop_recording()
        self.transcriber.stop()
        
        if self._processing_thread:
            self._processing_thread.join(timeout=5.0)
            
        if self.wake_detector:
            self.wake_detector.reset()
            
        if self.porcupine_detector:
            self.porcupine_detector.delete()
            
        logger.info("RealtimeSTT stopped")
        
    def _process_audio_chunk(self, audio_chunk: np.ndarray):
        if not self.is_activated and self.porcupine_detector and self.porcupine_detector.porcupine:
            if len(audio_chunk) == self.porcupine_detector.frame_length:
                keyword_index = self.porcupine_detector.process_audio(audio_chunk)
                if keyword_index is not None:
                    self._activate()
                    return
                    
        if self.vad and self.is_activated:
            frame_size = int(self.sample_rate * 0.03)
            
            for i in range(0, len(audio_chunk) - frame_size + 1, frame_size):
                frame = audio_chunk[i:i + frame_size]
                is_speech, state_changed = self.vad.process_audio(frame)
                
                if is_speech:
                    if not self.is_recording:
                        self._start_recording()
                    self.audio_buffer.append(frame)
                    self.silence_start = None
                else:
                    if self.is_recording:
                        self.audio_buffer.append(frame)
                        if self.silence_start is None:
                            self.silence_start = time.time()
                        elif time.time() - self.silence_start > self.max_silence_duration:
                            self._stop_recording()
                            
        elif self.is_activated:
            if not self.is_recording:
                self._start_recording()
            self.audio_buffer.append(audio_chunk)
            
        if self.is_recording and len(self.audio_buffer) > 0:
            audio_data = np.concatenate(self.audio_buffer)
            if len(audio_data) > self.sample_rate * 0.5:
                self.transcriber.add_audio(audio_data)
                self.audio_buffer = []
                
    def _start_recording(self):
        self.is_recording = True
        self.audio_buffer = []
        self.silence_start = None
        
        if self.on_start_recording:
            self.on_start_recording()
            
        print(f"{Fore.GREEN}Recording...{Style.RESET_ALL}")
        
    def _stop_recording(self):
        if len(self.audio_buffer) > 0:
            audio_data = np.concatenate(self.audio_buffer)
            self.transcriber.add_audio(audio_data)
            
        self.is_recording = False
        self.audio_buffer = []
        self.silence_start = None
        
        if self.vad:
            self.vad.reset()
            
        if self.on_stop_recording:
            self.on_stop_recording()
            
        print(f"{Fore.YELLOW}Processing...{Style.RESET_ALL}")
        
        if self.use_wake_word:
            self.is_activated = False
            
    def _activate(self):
        self.is_activated = True
        
        if self.on_wake_word:
            self.on_wake_word()
            
        print(f"{Fore.GREEN}Wake word detected! Listening...{Style.RESET_ALL}")
        
    def _on_transcription(self, text: str, info: Dict[str, Any]):
        if not text.strip():
            return
            
        if not self.is_activated and self.wake_detector:
            if self.wake_detector.process_audio(np.array([], dtype=np.int16), text):
                self._activate()
                return
                
        self._transcription_queue.put((text, info))
        
    def _process_transcriptions(self):
        while self.is_running:
            try:
                text, info = self._transcription_queue.get(timeout=0.1)
                
                print(f"{Fore.WHITE}Transcription: {text}{Style.RESET_ALL}")
                
                if self.on_transcription:
                    self.on_transcription(text)
                    
                if self.use_wake_word and not self.is_recording:
                    print(f"{Fore.CYAN}Listening for wake word '{self.wake_word}'...{Style.RESET_ALL}")
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing transcription: {e}")
                
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()