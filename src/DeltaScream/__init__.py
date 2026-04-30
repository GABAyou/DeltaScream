from .SourceCapture import VideoSource, AudioSource
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
                                        
        self.audio_source = AudioSource(mux_audio=mux_audio, 
                                        audio_callback=self.hub.audio_callback, 
                                        verbose=self.verbose)
                                        
        # 3. Initialize Watchdog
        self.scream_monitor = ScreamMonitor(delta_hub=self.hub, verbose=self.verbose)
        
        # Start Threads
        self.video_source.start()
        self.audio_source.start()
        self.scream_monitor.start()
        
        self.tributary = None
        
        if self.verbose:
            print("[DeltaStream] Multiplexer Online. Duplex Stream Active.")
            
    def read_video(self):
        """ Returns (success, frame) from the multiplexer. """
        return self.hub.read_video()
        
    def read_audio(self, index_from=0):
        """ Returns (new_index, list_of_chunks) from the multiplexer. """
        return self.hub.read_audio(index_from)
        
    def start_recording(self, video_path="output.mp4", audio_path="output.wav"):
        """ Forks a background Tributary to record the streams natively. """
        if self.tributary is None or not self.tributary.running:
            self.tributary = RecorderTributary(delta_hub=self.hub, 
                                               video_path=video_path, 
                                               audio_path=audio_path,
                                               target_fps=self.video_source.target_fps,
                                               audio_rate=self.audio_source.rate,
                                               verbose=self.verbose)
            self.tributary.start()
            
    def stop_recording(self):
        """ Stops the background Tributary. """
        if self.tributary and self.tributary.running:
            self.tributary.stop()
            self.tributary.join()
            
    def stop(self):
        """ Shuts down the entire DeltaStream duplex. """
        self.stop_recording()
        self.scream_monitor.stop()
        self.video_source.stop()
        self.audio_source.stop()
        
        self.scream_monitor.join()
        self.video_source.join()
        self.audio_source.join()
        
        if self.verbose:
            print("[DeltaStream] Multiplexer Offline.")
