import cv2
import pyaudiowpatch as pyaudio
import threading
import time

class VideoSource(threading.Thread):
    def __init__(self, src=0, target_fps=30, frame_callback=None, verbose=True):
        super().__init__(daemon=True)
        self.src = src
        self.target_fps = target_fps
        self.frame_callback = frame_callback
        self.verbose = verbose
        
        self.cap = cv2.VideoCapture(self.src)
        self.running = False
        
        if not self.cap.isOpened():
            if self.verbose:
                print(f"[DeltaScream] FAILED to open video source {self.src}")
        else:
            self.running = True
            if self.verbose:
                print(f"[DeltaStream] Video Source {self.src} Hooked.")
                
    def run(self):
        delay = 1.0 / self.target_fps
        while self.running and self.cap.isOpened():
            start = time.perf_counter()
            ret, frame = self.cap.read()
            
            if ret and self.frame_callback:
                self.frame_callback(frame)
                
            elapsed = time.perf_counter() - start
            sleep_t = max(0.001, delay - elapsed)
            time.sleep(sleep_t)
            
    def stop(self):
        self.running = False
        if self.cap.isOpened():
            self.cap.release()
        if self.verbose:
            print("[DeltaStream] Video Source Released.")


class AudioSource(threading.Thread):
    def __init__(self, mux_audio=True, audio_callback=None, verbose=True):
        super().__init__(daemon=True)
        self.mux_audio = mux_audio
        self.audio_callback = audio_callback
        self.verbose = verbose
        self.running = False
        
        self.p = pyaudio.PyAudio()
        
        # Resolve Devices
        try:
            self.mic_idx = self.p.get_default_input_device_info()["index"]
        except Exception:
            self.mic_idx = None
            
        try:
            wasapi_info = self.p.get_default_wasapi_loopback()
            self.speaker_idx = wasapi_info["index"]
        except OSError:
            try:
                self.speaker_idx = self.p.get_default_output_device_info()["index"]
            except Exception:
                self.speaker_idx = None
                
        # We will use the mic's rate as standard, or default to 44100
        self.rate = 44100
        if self.mic_idx is not None:
            self.rate = int(self.p.get_device_info_by_index(self.mic_idx)["defaultSampleRate"])
            
        self.mic_stream = None
        self.speaker_stream = None
        self.chunk = 1024
        
        if self.mic_idx is not None:
            self.mic_stream = self.p.open(format=pyaudio.paInt16,
                                          channels=1, # mono mic usually
                                          rate=self.rate,
                                          input=True,
                                          input_device_index=self.mic_idx,
                                          frames_per_buffer=self.chunk)
                                          
        if self.speaker_idx is not None and self.mux_audio:
            # WASAPI loopback needs to match its native format/channels exactly
            spk_info = self.p.get_device_info_by_index(self.speaker_idx)
            self.spk_channels = spk_info["maxInputChannels"]
            if self.spk_channels == 0: self.spk_channels = 2
            
            self.speaker_stream = self.p.open(format=pyaudio.paInt16,
                                              channels=self.spk_channels,
                                              rate=self.rate,
                                              input=True,
                                              input_device_index=self.speaker_idx,
                                              frames_per_buffer=self.chunk)
                                              
        if self.verbose:
            print(f"[DeltaStream] Audio Source Hooked. Mic: {self.mic_idx is not None}, System: {self.speaker_stream is not None}")
        self.running = True

    def run(self):
        while self.running:
            mic_data = None
            spk_data = None
            
            if self.mic_stream:
                try:
                    mic_data = self.mic_stream.read(self.chunk, exception_on_overflow=False)
                except Exception:
                    pass
                    
            if self.speaker_stream:
                try:
                    spk_data = self.speaker_stream.read(self.chunk, exception_on_overflow=False)
                except Exception:
                    pass
            
            if self.audio_callback:
                # Callback receives a tuple of (mic_data, spk_data)
                # If mux_audio=False, spk_data will be None.
                self.audio_callback((mic_data, spk_data))
                
    def stop(self):
        self.running = False
        if self.mic_stream:
            self.mic_stream.stop_stream()
            self.mic_stream.close()
        if self.speaker_stream:
            self.speaker_stream.stop_stream()
            self.speaker_stream.close()
        self.p.terminate()
        if self.verbose:
            print("[DeltaStream] Audio Source Released.")
