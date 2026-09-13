"""Standalone mic + Vosk diagnostic. Run this and talk -- it prints every
partial and final transcript Vosk produces, plus periodic audio level
readouts, so we can see whether audio is reaching Vosk at all vs. whether
it's just not recognizing the word cleanly.

    venv\\Scripts\\python scripts\\debug_voice.py
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import vosk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from robo_view import config as cfg

vosk.SetLogLevel(-1)

print("Input devices:")
print(sd.query_devices())
print("Default input device index:", sd.default.device[0])
print()

model = vosk.Model(str(cfg.MODEL_DIR))
grammar = json.dumps([" ".join(cfg.VOICE_GRAMMAR_WORDS), "[unk]"])
print("Grammar:", grammar, "\n")
rec = vosk.KaldiRecognizer(model, cfg.SAMPLE_RATE, grammar)

last_partial = ""
level_accum = []
last_level_print = time.monotonic()


def callback(indata, frames, time_info, status):
    global last_partial, last_level_print
    if status:
        print("STREAM STATUS:", status)

    block = indata[:, 0]
    level_accum.append(float(np.abs(block).mean()))

    now = time.monotonic()
    if now - last_level_print > 1.0:
        avg_level = sum(level_accum) / len(level_accum) if level_accum else 0
        bar = "#" * int(min(50, avg_level / 50))
        print(f"level: {avg_level:7.1f} |{bar}")
        level_accum.clear()
        last_level_print = now

    data = block.tobytes()
    if rec.AcceptWaveform(data):
        text = json.loads(rec.Result()).get("text", "")
        if text:
            print(f"FINAL:   {text!r}")
    else:
        partial = json.loads(rec.PartialResult()).get("partial", "")
        if partial and partial != last_partial:
            last_partial = partial
            print(f"partial: {partial!r}")


print("Listening... say 'grid', 'target', 'follow', 'stress', 'playback'.")
print("Ctrl+C to stop.\n")

with sd.InputStream(samplerate=cfg.SAMPLE_RATE, blocksize=cfg.AUDIO_BLOCK_SIZE,
                     channels=1, dtype="int16", callback=callback):
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nstopped")
