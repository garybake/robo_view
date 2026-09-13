"""One microphone, multiple listeners.

Both the voice-command spotter and the stress analyzer need live mic audio.
Opening two separate sounddevice streams against the same device is a good
way to get 'device busy' errors on Windows, so instead we open a single
InputStream here and fan every audio block out to whoever subscribed.
"""

import threading

import numpy as np
import sounddevice as sd

from . import config as cfg


class AudioHub:
    def __init__(self, samplerate=cfg.SAMPLE_RATE, blocksize=cfg.AUDIO_BLOCK_SIZE):
        self.samplerate = samplerate
        self.blocksize = blocksize
        self._subscribers = []
        self._lock = threading.Lock()
        self._stream = None

    def subscribe(self, callback):
        """callback(block: np.ndarray[int16, mono]) -> None, called from the
        audio thread. Keep it fast and non-blocking."""
        with self._lock:
            self._subscribers.append(callback)

    def _on_audio(self, indata, frames, time_info, status):
        if status:
            # Overflows etc. -- not fatal, just log-worthy in a real app.
            pass
        block = indata[:, 0].copy()
        with self._lock:
            subs = list(self._subscribers)
        for cb in subs:
            try:
                cb(block)
            except Exception:
                # A misbehaving subscriber shouldn't kill the audio thread.
                pass

    def start(self):
        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            channels=1,
            dtype="int16",
            callback=self._on_audio,
        )
        self._stream.start()

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None


def int16_block_to_float(block: np.ndarray) -> np.ndarray:
    return block.astype(np.float32) / 32768.0
