"""'Voice stress analyzer' -- real pitch/jitter/shimmer measurements via
Parselmouth (Praat bindings), fed from a rolling per-speaker audio buffer.

Voice stress analysis as a lie-detection technique is pseudoscience, for
the record -- but the numbers going into the meter (F0 mean/std, jitter,
shimmer) are genuine acoustic measurements, not a fake needle wiggle.

Since we only have one microphone, "two voices" is handled by the operator
toggling `active_speaker` (bound to keys 1/2 in the main loop) to say who's
talking right now -- there's no real-time speaker diarization here.
"""

import collections
import time

import numpy as np
import parselmouth

from . import config as cfg
from .audio_hub import int16_block_to_float


class VoiceStressAnalyzer:
    def __init__(self, audio_hub):
        self.active_speaker = 1
        self.enabled = False  # main loop flips this on/off with the state machine

        chunks_per_buffer = int(cfg.STRESS_BUFFER_SECONDS * cfg.SAMPLE_RATE / cfg.AUDIO_BLOCK_SIZE) + 2
        self._buffers = {
            1: collections.deque(maxlen=chunks_per_buffer),
            2: collections.deque(maxlen=chunks_per_buffer),
        }
        self._last_analysis_time = 0.0
        self.results = {1: None, 2: None}

        audio_hub.subscribe(self._on_audio_block)

    def _on_audio_block(self, block):
        if not self.enabled:
            return
        samples = int16_block_to_float(block)
        self._buffers[self.active_speaker].append(samples)

    def _recent_window(self, speaker, seconds):
        buf = self._buffers[speaker]
        if not buf:
            return None
        arr = np.concatenate(list(buf))
        n = int(seconds * cfg.SAMPLE_RATE)
        if arr.size < n:
            return arr if arr.size > 0 else None
        return arr[-n:]

    def maybe_analyze(self):
        """Call every frame; internally throttled to STRESS_UPDATE_INTERVAL."""
        now = time.monotonic()
        if now - self._last_analysis_time < cfg.STRESS_UPDATE_INTERVAL:
            return self.results
        self._last_analysis_time = now
        self.results[1] = self._analyze_speaker(1)
        self.results[2] = self._analyze_speaker(2)
        return self.results

    def _analyze_speaker(self, speaker):
        window = self._recent_window(speaker, cfg.STRESS_WINDOW_SECONDS)
        if window is None or window.size < int(cfg.SAMPLE_RATE * 0.3):
            return None

        rms = float(np.sqrt(np.mean(window ** 2)))
        if rms < 0.005:
            return None  # essentially silence, nothing to measure

        try:
            sound = parselmouth.Sound(window, sampling_frequency=cfg.SAMPLE_RATE)
            pitch = sound.to_pitch()
            f0 = pitch.selected_array["frequency"]
            f0 = f0[f0 > 0]
            if f0.size < 3:
                return None
            f0_mean, f0_std = float(np.mean(f0)), float(np.std(f0))

            point_process = parselmouth.praat.call(
                sound, "To PointProcess (periodic, cc)", 75, 500
            )
            jitter = parselmouth.praat.call(
                point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3
            )
            shimmer = parselmouth.praat.call(
                [sound, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6
            )
            jitter = 0.0 if jitter is None or jitter != jitter else float(jitter)
            shimmer = 0.0 if shimmer is None or shimmer != shimmer else float(shimmer)

            stress_index = (
                min(1.0, jitter / 0.03) * 40
                + min(1.0, shimmer / 0.15) * 30
                + min(1.0, f0_std / 40) * 30
            )
            return {
                "f0_mean": f0_mean,
                "f0_std": f0_std,
                "jitter": jitter,
                "shimmer": shimmer,
                "stress": stress_index,
            }
        except Exception:
            return None
