"""Rolling frame buffer + replay controller for the 'playback' command.

The main loop pushes every live frame in here regardless of state, so the
last N seconds are always available. Saying 'playback' freezes the live
feed and replays that buffer in a loop until another command is heard.
"""

import collections

from . import config as cfg


class FrameRingBuffer:
    def __init__(self, fps=cfg.TARGET_FPS, seconds=cfg.PLAYBACK_SECONDS):
        self._buffer = collections.deque(maxlen=int(fps * seconds))

    def push(self, frame):
        self._buffer.append(frame.copy())

    def snapshot(self):
        """Copy out the current contents as a list, oldest first."""
        return list(self._buffer)

    def __len__(self):
        return len(self._buffer)


class PlaybackController:
    def __init__(self):
        self.frames = []
        self.index = 0
        self.active = False

    def start(self, frames):
        self.frames = frames
        self.index = 0
        self.active = bool(frames)

    def stop(self):
        self.active = False
        self.frames = []
        self.index = 0

    def next_frame(self):
        """Returns the next frame to display, looping back to the start
        when it reaches the end. Returns None if there's nothing buffered."""
        if not self.frames:
            return None
        frame = self.frames[self.index]
        self.index = (self.index + 1) % len(self.frames)
        return frame

    @property
    def progress(self):
        if not self.frames:
            return 0.0
        return self.index / len(self.frames)
