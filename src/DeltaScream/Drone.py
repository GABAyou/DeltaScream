import pyaudiowpatch as pyaudio
import numpy as np
import threading

class DroneGenerator(threading.Thread):
    def __init__(self, frequency=136.1, beat_hz=4.0, volume=0.05):
        """
        Generates a continuous isochronic drone strictly in the Right channel.
        Keeps the WASAPI loopback active to prevent PyAudio blocking.
        """
        super().__init__(daemon=True)
        self.frequency = frequency
        self.beat_hz = beat_hz
        self.volume = volume
        self.running = False
        
        self.p = pyaudio.PyAudio()
        self.sample_rate = 48000 # Use 48kHz for better WASAPI compatibility
        
        try:
            # We output to the default system speaker (which WASAPI loopback captures)
            self.stream = self.p.open(
                format=pyaudio.paFloat32,
                channels=2, # Stereo!
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=1024
            )
        except Exception as e:
            print(f"[!] DeltaScream Drone Failed to open output stream: {e}")
            self.stream = None

    def run(self):
        if not self.stream:
            return
            
        self.running = True
        t = 0.0
        chunk_size = 1024
        
        while self.running:
            time_array = np.arange(chunk_size) / self.sample_rate + t
            carrier = np.sin(2 * np.pi * self.frequency * time_array)
            modulator = (np.sin(2 * np.pi * self.beat_hz * time_array) + 1) / 2.0
            
            right_channel = (carrier * modulator * self.volume).astype(np.float32)
            
            # Interleave into stereo: [Left, Right, Left, Right...]
            stereo_chunk = np.zeros(chunk_size * 2, dtype=np.float32)
            # Left channel stays 0.0 (silence)
            stereo_chunk[1::2] = right_channel
            
            try:
                self.stream.write(stereo_chunk.tobytes())
            except Exception:
                pass
                
            t += chunk_size / self.sample_rate

    def stop(self):
        self.running = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
        self.p.terminate()
