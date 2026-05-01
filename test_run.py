import cv2
import time
import datetime
from src.DeltaScream import DeltaScream

def main():
    print("Initializing DeltaScream Hub...")
    # Initialize the multiplexer with camera 0 and audio multiplexing enabled
    hub = DeltaScream(video_src=0, mux_audio=True, verbose=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    vid_path = f"test_video_{timestamp}.mp4"
    aud_path = f"test_audio_{timestamp}.wav"
    
    print(f"Starting background Tributary recording...\n Video: {vid_path}\n Audio: {aud_path}")
    # This forks the stream and writes it to disk natively
    hub.start_recording(vid_path, aud_path)
    
    print("Entering Main Inference Loop (Press 'q' to quit)...")
    try:
        while True:
            # Emulate an AI inference loop fetching the latest frame
            success, frame = hub.read_video()
            
            if success and frame is not None:
                # Show the frame we pulled from the Delta
                cv2.imshow("DeltaScream Main Stream", frame)
                
            # Press 'q' to break out of the loop
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
            # Sleep slightly to emulate processing time (the watchdog should scream if this is too slow)
            time.sleep(0.03)
            
    except KeyboardInterrupt:
        print("Interrupted by user.")
        
    finally:
        print("Shutting down DeltaScream...")
        cv2.destroyAllWindows()
        hub.stop() # This automatically stops the tributary as well
        print("Test complete. Check for test_video.mp4 and test_audio.wav in your folder.")

if __name__ == "__main__":
    main()
