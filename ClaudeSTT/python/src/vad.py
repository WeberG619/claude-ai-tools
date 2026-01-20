import numpy as np
import torch
import torchaudio
from typing import Tuple, Optional
import logging

try:
    import webrtcvad
except ImportError:
    import webrtcvad_wheels as webrtcvad

logger = logging.getLogger(__name__)

class VoiceActivityDetector:
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        padding_duration_ms: int = 300,
        webrtc_mode: int = 3,
        use_silero: bool = True
    ):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.padding_duration_ms = padding_duration_ms
        
        self.webrtc_vad = webrtcvad.Vad(webrtc_mode)
        
        self.use_silero = use_silero
        self.silero_model = None
        if use_silero:
            try:
                self.silero_model, utils = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    force_reload=False,
                    onnx=False
                )
                self.get_speech_timestamps = utils[0]
                logger.info("Silero VAD loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load Silero VAD: {e}. Falling back to WebRTC VAD only.")
                self.use_silero = False
                
        self.num_padding_frames = int(padding_duration_ms / frame_duration_ms)
        self.ring_buffer = []
        self.triggered = False
        
    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        if len(audio_chunk) * 1000 // self.sample_rate != self.frame_duration_ms:
            return False
            
        is_speech = self.webrtc_vad.is_speech(audio_chunk.tobytes(), self.sample_rate)
        
        if is_speech and self.use_silero and self.silero_model:
            try:
                audio_tensor = torch.from_numpy(audio_chunk).float() / 32768.0
                speech_prob = self.silero_model(audio_tensor.unsqueeze(0), self.sample_rate).item()
                is_speech = speech_prob > 0.5
            except Exception as e:
                logger.debug(f"Silero VAD check failed: {e}")
                
        return is_speech
        
    def process_audio(self, audio_chunk: np.ndarray) -> Tuple[bool, bool]:
        is_speech = self.is_speech(audio_chunk)
        
        if not self.triggered:
            self.ring_buffer.append((audio_chunk, is_speech))
            num_voiced = len([f for f, speech in self.ring_buffer if speech])
            
            if num_voiced > 0.5 * self.num_padding_frames:
                self.triggered = True
                return True, True
            else:
                if len(self.ring_buffer) > self.num_padding_frames:
                    self.ring_buffer.pop(0)
                return False, False
        else:
            self.ring_buffer.append((audio_chunk, is_speech))
            num_unvoiced = len([f for f, speech in self.ring_buffer[-self.num_padding_frames:] if not speech])
            
            if num_unvoiced > 0.9 * self.num_padding_frames:
                self.triggered = False
                self.ring_buffer = []
                return False, True
            else:
                if len(self.ring_buffer) > self.num_padding_frames:
                    self.ring_buffer.pop(0)
                return True, False
                
    def reset(self):
        self.ring_buffer = []
        self.triggered = False
        
    def get_speech_timestamps_from_audio(self, audio: np.ndarray) -> list:
        if not self.use_silero or not self.silero_model:
            return []
            
        try:
            audio_tensor = torch.from_numpy(audio).float() / 32768.0
            timestamps = self.get_speech_timestamps(
                audio_tensor,
                self.silero_model,
                sampling_rate=self.sample_rate
            )
            return timestamps
        except Exception as e:
            logger.error(f"Failed to get speech timestamps: {e}")
            return []