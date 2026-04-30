import cv2
import wave
import threading
import time

class RecorderTributary(threading.Thread):
    """
    A low-priority background thread that drains the Delta buffers 
    into a video file and an audio file without stealing inference CPU cycles.
    """
    def __init__(self, delta_hub, video_path="output.mp4", audio_path="output.wav", 
                 target_fps=15, audio_rate=44100, verbose=True):
        super().__init__(daemon=True)
        self.delta_hub = delta_hub
        self.video_path = video_path
        self.audio_path = audio_path
        self.target_fps = target_fps
        self.audio_rate = audio_rate
        self.verbose = verbose
        
        self.running = False
        self.video_writer = None
        self.audio_writer = None
        self.audio_index = 0
        
    def run(self):
        self.running = True
        
        delay = 1.0 / self.target_fps
        
        if self.verbose:
            print(f"[DeltaStream: Tributary] Recording started -> {self.video_path}")
            
        while self.running:
            start = time.perf_counter()
            
            # --- 1. Drain Video ---
            success, frame = self.delta_hub.read_video()
            if success:
                if self.video_writer is None:
                    h, w, _ = frame.shape
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    self.video_writer = cv2.VideoWriter(self.video_path, fourcc, self.target_fps, (w, h))
                
                self.video_writer.write(frame)
                
            # --- 2. Drain Audio ---
            self.audio_index, chunks = self.delta_hub.read_audio(self.audio_index)
            
            if chunks:
                if self.audio_writer is None:
                    # Determine channels based on the first chunk
                    # chunks[0] is (mic_data, spk_data)
                    mic_data, spk_data = chunks[0]
                    channels = 1 if (mic_data and not spk_data) else 2
                    
                    self.audio_writer = wave.open(self.audio_path, 'wb')
                    self.audio_writer.setnchannels(channels)
                    self.audio_writer.setsampwidth(2) # paInt16 is 2 bytes
                    self.audio_writer.setframerate(self.audio_rate)
                    
                for mic_data, spk_data in chunks:
                    # If we only have mic_data, just write it.
                    # If we have both, we interleave them for stereo (Mic L, Spk R)
                    # For simplicity in this Tributary, we just write what we have.
                    if mic_data and spk_data:
                        self.audio_writer.writeframes(mic_data)
                    elif mic_data:
                        self.audio_writer.writeframes(mic_data)
                    elif spk_data:
                        self.audio_writer.writeframes(spk_data)

            # Sleep to match video framerate (Audio doesn't care since we read chunks)
            elapsed = time.perf_counter() - start
            sleep_t = max(0.001, delay - elapsed)
            time.sleep(sleep_t)
            
        # Cleanup
        if self.video_writer:
            self.video_writer.release()
        if self.audio_writer:
            self.audio_writer.close()
            
        if self.verbose:
            print(f"[DeltaStream: Tributary] Recording finalized.")

    def stop(self):
        self.running = False
