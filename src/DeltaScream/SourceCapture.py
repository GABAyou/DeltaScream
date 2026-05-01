import cv2
import pyaudiowpatch as pyaudio
import threading
import time
import mss
import numpy as np
from .Drone import DroneGenerator

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
                print(f"[DeltaScream] Video Source {self.src} Hooked.")
                
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
            print("[DeltaScream] Video Source Released.")


class ScreenSource(threading.Thread):
    def __init__(self, target_fps=30, frame_callback=None, verbose=True):
        super().__init__(daemon=True)
        self.target_fps = target_fps
        self.frame_callback = frame_callback
        self.verbose = verbose
        self.running = False
        
        try:
            self.sct = mss.mss()
            # monitor 1 is usually the primary monitor
            self.monitor = self.sct.monitors[1] 
            self.running = True
            if self.verbose:
                print("[DeltaScream] Screen Source Hooked.")
        except Exception as e:
            if self.verbose:
                print(f"[DeltaScream] FAILED to open screen source: {e}")
                
    def run(self):
        delay = 1.0 / self.target_fps
        while self.running:
            start = time.perf_counter()
            
            try:
                sct_img = self.sct.grab(self.monitor)
                # Convert to numpy array (BGRA) and drop alpha channel (BGR)
                frame = np.array(sct_img)[:, :, :3]
                
                if self.frame_callback:
                    self.frame_callback(frame)
            except Exception as e:
                print(f"[DeltaScream Screen Error] {e}")
                
            elapsed = time.perf_counter() - start
            sleep_t = max(0.001, delay - elapsed)
            time.sleep(sleep_t)
            
    def stop(self):
        self.running = False
        if hasattr(self, 'sct'):
            self.sct.close()
        if self.verbose:
            print("[DeltaScream] Screen Source Released.")



class AudioSource(threading.Thread):
    def __init__(self, mux_audio=True, audio_callback=None, verbose=True):
        super().__init__(daemon=True)
        self.mux_audio = mux_audio
        self.audio_callback = audio_callback
        self.verbose = verbose
        self.running = False
        self.drone = None
        
        if self.mux_audio:
            self.drone = DroneGenerator()
            self.drone.start()

        
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
                
        # We will use WASAPI loopback rate as standard because it's strictly enforced.
        self.rate = 48000
        if self.speaker_idx is not None:
            self.rate = int(self.p.get_device_info_by_index(self.speaker_idx)["defaultSampleRate"])
        elif self.mic_idx is not None:
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
            try:
                mic_data = None
                spk_data = None
                
                if self.mic_stream:
                    try:
                        mic_data = self.mic_stream.read(self.chunk, exception_on_overflow=False)
                    except Exception as e:
                        print(f"[DeltaScream Mic Error] {e}")
                        
                if self.speaker_stream:
                    try:
                        spk_data = self.speaker_stream.read(self.chunk, exception_on_overflow=False)
                    except Exception as e:
                        print(f"[DeltaScream Speaker Error] {e}")
                
                if self.audio_callback:
                    self.audio_callback((mic_data, spk_data))
                    
            except Exception as main_e:
                print(f"[DeltaScream AudioSource Error] {main_e}")
                import traceback
                traceback.print_exc()
                
    def stop(self):
        self.running = False
        if self.drone:
            self.drone.stop()
        if self.mic_stream:
            self.mic_stream.stop_stream()
            self.mic_stream.close()
        if self.speaker_stream:
            self.speaker_stream.stop_stream()
            self.speaker_stream.close()
        self.p.terminate()
        if self.verbose:
            print("[DeltaScream] Audio Source Released.")
