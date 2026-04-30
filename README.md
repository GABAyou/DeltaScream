# DeltaScream

A high-performance media "delta" that forks raw audio/video buffers into multiple concurrent streams.

When building AI tools (like Neural Inference engines or Computer Vision apps), they often "hog" the hardware. You lose the ability to screen record or tap into the audio because your inference engine places an exclusive lock on your OS drivers.

**DeltaScream** acts as a buffered middleware. Instead of your apps reaching for the hardware, they reach for the Delta.

- **The Main Branch (Inference):** A high-priority, low-latency path for your neural logic.
- **The Side Branch (Recording):** A background "Tributary" that encodes the frames and audio to a file natively.
- **The Scream Listener:** A watchdog thread that monitors the buffer health. If the inference engine causes a bottleneck, it triggers the "Scream" state.

## Installation
```bash
pip install DeltaScream
```

## Quick Start
```python
from DeltaScream import DeltaScream

# Initialize the Hub (Dual-Stream Default: Mic + System WASAPI)
hub = DeltaScream(video_src=0, mux_audio=True)

# To get the latest video frame for your inference engine:
success, frame = hub.read_video()

# To get the latest sequential audio frames (to avoid stuttering):
# Maintain your own local index
my_audio_index = 0
audio_chunks = hub.read_audio(my_audio_index)
my_audio_index += len(audio_chunks)

# To start the built-in background recorder (Tributary):
hub.start_recording("my_session.mp4", "my_session_audio.wav")
hub.stop_recording()

# Shutdown
hub.stop()
```
