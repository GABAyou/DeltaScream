import threading
import time

class ScreamMonitor(threading.Thread):
    """
    A watchdog that monitors the health of the DeltaStream buffers.
    If the inference engine (or other process) hogs the CPU and causes
    buffer overflows or extreme frame drops, this thread will 'Scream'.
    """
    def __init__(self, delta_hub, scream_threshold=9000, verbose=True):
        super().__init__(daemon=True)
        self.delta_hub = delta_hub
        # If the audio buffer approaches the max history, someone isn't reading it fast enough
        self.scream_threshold = scream_threshold 
        self.verbose = verbose
        self.running = False
        
    def run(self):
        self.running = True
        
        while self.running:
            # Check Audio Buffer Health
            current_len = len(self.delta_hub.audio_frames)
            
            if current_len > self.scream_threshold:
                self.scream()
                
            time.sleep(2.0) # Check every 2 seconds
            
    def scream(self):
        if self.verbose:
            print("\n" + "="*60)
            print(">> [DeltaScream]: I LITERALLY CANNOT HEAR OVER THE INFERENCE ENGINE.")
            print(">> ERROR: AUDIO BUFFER OVERFLOW DETECTED. CPU CONTENTION CRITICAL.")
            print("="*60 + "\n")
            # In a full implementation, you could trigger a winsound.Beep() here.

    def stop(self):
        self.running = False
