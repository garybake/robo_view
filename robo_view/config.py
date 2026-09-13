"""Shared constants and tuning knobs for the RoboCop-style calibration rig."""

from pathlib import Path

# --- paths -------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT_DIR / "models" / "vosk-model-small-en-us-0.15"

# --- camera --------------------------------------------------------------
CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
TARGET_FPS = 30

# --- audio ---------------------------------------------------------------
SAMPLE_RATE = 16000
AUDIO_BLOCK_SIZE = 4000  # 0.25s chunks @ 16kHz, good balance of latency vs. Vosk accuracy

# --- voice commands --------------------------------------------------------
# Substring keywords matched against Vosk's recognized text. Order doesn't
# matter; first match in a recognized phrase wins. Cooldown stops one
# utterance from re-triggering the same command many times as partials firm up.
VOICE_COMMANDS = {
    "grid": ["grid"],
    "target": ["target"],
    "follow": ["follow"],
    "stress": ["stress", "voice stress"],
    "playback": ["playback", "play back"],
    "reset": ["reset", "stand down"],
}
COMMAND_COOLDOWN_SECONDS = 1.5

# Vosk's open-vocabulary decoder happily mishears "grid" as "great" -- with
# only a handful of commands to tell apart, constraining it to a fixed
# grammar (our vocabulary + a catch-all "[unk]" bucket for everything else)
# is far more accurate than letting it guess from all of English.
VOICE_GRAMMAR_WORDS = sorted({
    word
    for keywords in VOICE_COMMANDS.values()
    for phrase in keywords
    for word in phrase.split()
})

# --- targeting -------------------------------------------------------------
TARGET_BOX_SIZE = 90  # px, square ROI seeded around a click for the tracker
FOLLOW_SMOOTHING = 0.35  # 0=no smoothing (snap), 1=frozen; lower = snappier

# --- playback --------------------------------------------------------------
PLAYBACK_SECONDS = 8

# --- voice stress analyzer ---------------------------------------------------
STRESS_WINDOW_SECONDS = 1.5  # analysis window fed to Parselmouth
STRESS_UPDATE_INTERVAL = 0.4  # seconds between re-analyses (Praat calls aren't free)
STRESS_BUFFER_SECONDS = 4  # rolling buffer kept per speaker

# --- HUD colors (BGR, OpenCV order) -----------------------------------------
COLOR_GREEN = (60, 255, 90)
COLOR_AMBER = (0, 190, 255)
COLOR_RED = (50, 50, 255)
COLOR_DIM_GREEN = (30, 120, 40)
FONT = 0  # cv2.FONT_HERSHEY_SIMPLEX, kept as int to avoid importing cv2 here
