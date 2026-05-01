from .SourceCapture import VideoSource, AudioSource, ScreenSource
from .TheDelta import TheDelta
from .RecorderTributary import RecorderTributary
from .DeltaScream import ScreamMonitor

class DeltaScream:
    """
    The main entry point for the DeltaScream package.
    Initializes the hardware sources, the multiplexer, and the watchdog.
    """
    def __init__(self, video_src=0, target_fps=30, mux_audio=True, verbose=True):
        self.verbose = verbose
        
        # 1. Initialize the Delta Buffer
        self.hub = TheDelta()
        
        # 2. Initialize Hardware Sources (passing the Delta callbacks)
        self.video_source = VideoSource(src=video_src, 
                                        target_fps=target_fps, 
                                        frame_callback=self.hub.video_callback, 
                                        verbose=self.verbose)
                                        
        self.screen_source = ScreenSource(target_fps=target_fps,
                                          frame_callback=self.hub.screen_callback,
                                          verbose=self.verbose)
                                          
        self.audio_source = AudioSource(mux_audio=mux_audio, 
                                        audio_callback=self.hub.audio_callback, 
                                        verbose=self.verbose)
                                        
        # 3. Initialize Watchdog
        self.scream_monitor = ScreamMonitor(delta_hub=self.hub, verbose=self.verbose)
        
        # Start Threads
        self.video_source.start()
        self.screen_source.start()
        self.audio_source.start()
        self.scream_monitor.start()
        
        self.tributary = None
        
        if self.verbose:
            print("[DeltaScream] Multiplexer Online. Matrix Router Active.")
            
    def read_video(self):
        """ Returns (success, frame) of the camera stream from the multiplexer. """
        return self.hub.read_video()
        
    def read_screen(self):
        """ Returns (success, frame) of the monitor stream from the multiplexer. """
        return self.hub.read_screen()
        
    def read_audio(self, index_from=0):
        """ Returns (new_index, list_of_chunks) from the multiplexer. """
        return self.hub.read_audio(index_from)
        
    def start_recording(self, video_path="output.mp4", audio_path="output.wav"):
        """ Forks a background Tributary to record the streams natively with PiP. """
        if self.tributary is None or not self.tributary.running:
            self.tributary = RecorderTributary(delta_hub=self.hub, 
                                               video_path=video_path, 
                                               audio_path=audio_path,
                                               target_fps=self.video_source.target_fps,
                                               audio_rate=self.audio_source.rate,
                                               verbose=self.verbose)
            self.tributary.start()
            
    def stop_recording(self):
        """ Stops the background Tributary. Auto-muxing will trigger if configured. """
        if self.tributary and self.tributary.running:
            self.tributary.stop()
            self.tributary.join()
            
    def stop(self):
        """ Shuts down the entire DeltaScream router. """
        self.stop_recording()
        self.scream_monitor.stop()
        self.video_source.stop()
        self.screen_source.stop()
        self.audio_source.stop()
        
        self.scream_monitor.join()
        self.video_source.join()
        self.screen_source.join()
        self.audio_source.join()
        
        if self.verbose:
            print("[DeltaScream] Multiplexer Offline.")

    @staticmethod
    def mux_media(video_path, audio_path, output_path=None):
        """
        Public utility to securely mux any video and audio file.
        Useful for manually combining Neural Inference videos with DeltaScream audio.
        """
        import subprocess
        import os
        
        if not output_path:
            base, ext = os.path.splitext(video_path)
            output_path = f"{base}_muxed{ext}"
            
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            output_path
        ]
        
        try:
            print(f"[DeltaScream] Muxing {video_path} + {audio_path}...")
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, shell=True)
            print(f"[DeltaScream] Muxing Complete: {output_path}")
            return True
        except Exception as e:
            print(f"[DeltaScream Error] Muxing failed. Make sure 'ffmpeg' is in your System PATH. {e}")
            return False
