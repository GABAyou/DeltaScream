import threading

class TheDelta:
    """
    The Multiplexer Hub.
    Maintains thread-safe infinite-consumer buffers for both Video and Audio.
    """
    def __init__(self, max_audio_history=10000):
        # Video is usually a single frame (the "Latest") because it's instantaneous state
        self.video_frame = None
        self.video_lock = threading.Lock()
        
        # Audio is sequential. We maintain a list of historical chunks.
        # Max history prevents memory leaks if left running for days.
        self.audio_frames = []
        self.max_audio_history = max_audio_history
        self.audio_lock = threading.Lock()
        
    def video_callback(self, frame):
        """ Called by SourceCapture when a new video frame arrives. """
        with self.video_lock:
            # We store a copy so readers don't get memory torn while writing
            self.video_frame = frame.copy()
            
    def audio_callback(self, data_tuple):
        """ Called by SourceCapture when new audio chunks arrive. """
        with self.audio_lock:
            self.audio_frames.append(data_tuple)
            # Prevent infinite memory growth
            if len(self.audio_frames) > self.max_audio_history:
                # Trim the oldest 10%
                trim_point = int(self.max_audio_history * 0.1)
                self.audio_frames = self.audio_frames[trim_point:]
                
    def read_video(self):
        """ Returns (success, frame). Infinite consumers can call this concurrently. """
        with self.video_lock:
            if self.video_frame is not None:
                return True, self.video_frame.copy()
            return False, None
            
    def read_audio(self, index_from=0):
        """ 
        Returns (new_index, list_of_chunks). 
        Consumers must pass their last known index to get only the new chunks.
        """
        with self.audio_lock:
            current_len = len(self.audio_frames)
            
            # Handle the case where the buffer was trimmed and the consumer's index is now invalid
            if current_len == self.max_audio_history and index_from < current_len - (self.max_audio_history * 0.9):
                # The buffer was trimmed past the consumer's index. 
                # We reset them to the beginning of the available history.
                index_from = 0
            elif index_from > current_len:
                # Should not happen unless buffer was hard reset
                index_from = 0
                
            chunks = self.audio_frames[index_from:]
            return current_len, chunks
