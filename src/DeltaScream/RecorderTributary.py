import cv2
import wave
import threading
import time
import numpy as np
import subprocess
import os

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
            try:
                start = time.perf_counter()
                
                # --- 1. Drain Video ---
                success, screen_frame = self.delta_hub.read_screen()
                cam_success, cam_frame = self.delta_hub.read_video()
                
                if success and self.video_path is not None:
                    # Picture-in-Picture Compositing
                    if cam_success and cam_frame is not None:
                        sh, sw, _ = screen_frame.shape
                        ch, cw, _ = cam_frame.shape
                        
                        # Scale camera to 20% of screen width
                        pip_w = int(sw * 0.2)
                        pip_h = int((pip_w / cw) * ch)
                        
                        pip_frame = cv2.resize(cam_frame, (pip_w, pip_h))
                        
                        # Bottom right corner padding
                        padding = 20
                        x_offset = sw - pip_w - padding
                        y_offset = sh - pip_h - padding
                        
                        # Overlay
                        screen_frame[y_offset:y_offset+pip_h, x_offset:x_offset+pip_w] = pip_frame
                        
                    if self.video_writer is None:
                        h, w, _ = screen_frame.shape
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        self.video_writer = cv2.VideoWriter(self.video_path, fourcc, self.target_fps, (w, h))
                    
                    self.video_writer.write(screen_frame)
                    
                # --- 2. Drain Audio ---
                self.audio_index, chunks = self.delta_hub.read_audio(self.audio_index)
                
                if chunks and self.audio_path is not None:
                    if self.audio_writer is None:
                        # Determine channels based on the first chunk
                        mic_data, spk_data = chunks[0]
                        channels = 1 if (mic_data and not spk_data) else 2
                        
                        self.audio_writer = wave.open(self.audio_path, 'wb')
                        self.audio_writer.setnchannels(channels)
                        self.audio_writer.setsampwidth(2) # paInt16 is 2 bytes
                        self.audio_writer.setframerate(int(self.audio_rate))
                        
                    for mic_data, spk_data in chunks:
                        if mic_data and spk_data:
                            mic_np = np.frombuffer(mic_data, dtype=np.int16)
                            spk_np = np.frombuffer(spk_data, dtype=np.int16)
                            
                            # Hard-Panned Stereo Mix:
                            # Left Channel = Mic (Mono)
                            # Right Channel = Speaker Right (Contains Drone)
                            if len(mic_np) * 2 == len(spk_np):
                                mixed = np.zeros(len(mic_np) * 2, dtype=np.int16)
                                mixed[0::2] = mic_np
                                mixed[1::2] = spk_np[1::2]
                                self.audio_writer.writeframes(mixed.tobytes())
                            else:
                                # Fallback if sizes don't match exactly
                                self.audio_writer.writeframes(spk_data)
                                
                        elif mic_data:
                            self.audio_writer.writeframes(mic_data)
                        elif spk_data:
                            self.audio_writer.writeframes(spk_data)

                # Sleep to match video framerate
                elapsed = time.perf_counter() - start
                sleep_t = max(0.001, delay - elapsed)
                time.sleep(sleep_t)
            except Exception as e:
                print(f"[DeltaScream Tributary Error] {e}")
                import traceback
                traceback.print_exc()
            
        # Cleanup
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            
        if self.audio_writer:
            self.audio_writer.close()
            self.audio_writer = None
            
        if self.verbose:
            print("[DeltaScream] Tributary Streams Closed.")
            
        # AUTO-MUXING
        if self.video_path and self.audio_path and os.path.exists(self.video_path) and os.path.exists(self.audio_path):
            if self.verbose:
                print(f"[DeltaScream] Auto-Muxing {self.video_path} + {self.audio_path}...")
                
            base, ext = os.path.splitext(self.video_path)
            muxed_path = f"{base}_muxed{ext}"
            
            # Use ffmpeg to combine the video and audio without re-encoding the video
            cmd = [
                "ffmpeg", "-y",
                "-i", self.video_path,
                "-i", self.audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                muxed_path
            ]
            try:
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, shell=True, text=True)
                if self.verbose:
                    print(f"[DeltaScream] Auto-Muxing Complete: {muxed_path}")
            except subprocess.CalledProcessError as e:
                print(f"[DeltaScream Error] Auto-Muxing failed with exit code {e.returncode}. ffmpeg Output:")
                print(e.stderr)
            except Exception as e:
                print(f"[DeltaScream Error] Auto-Muxing failed. {e}")

    def stop(self):
        self.running = False
