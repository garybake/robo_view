# robo_view

A RoboCop-calibration-scene, rebuilt with a webcam and a bit of nostalgia.

https://youtu.be/2z8tQqZG8gI?si=EKclIfflEjiVdEFe&t=305

> "We'd like you to try the targeting scanner..."

Say the word, watch it happen:

| Say...        | Does...                                                             |
|---------------|----------------------------------------------------------------------|
| **"grid"**    | Draws the targeting grid + center crosshair                          |
| **"target"**  | Click on something in the video window to lock the tracker onto it   |
| **"follow"**  | Continuously tracks whatever you targeted (needs a target first)     |
| **"stress"**  | Voice stress analyzer -- press `1`/`2` to say who's currently talking |
| **"playback"**| Replays the last 8 seconds on a loop                                  |
| **"reset"**   | Back to idle                                                          |

Keys `1`/`2` pick the active speaker while in stress mode. `q` / `Esc` quits.
Keys `g`/`t`/`f`/`s`/`p`/`r` are a manual fallback for the same five commands,
in case the mic isn't cooperating -- voice is the intended interface.

## How it works

- **Video feed**: plain OpenCV `VideoCapture` + `imshow` loop.
- **Targeting**: no YOLO needed here -- a pen isn't a COCO class anyway.
  Instead, click once to seed an OpenCV CSRT tracker on whatever's under the
  crosshair, then it reports the tracked box every frame.
- **Voice commands**: fully offline, via [Vosk](https://alphacephei.com/vosk/)
  small English model + free-form keyword spotting (no rigid grammar, so
  natural phrasing like "okay, give me a grid" still triggers "grid").
- **Voice stress analyzer**: real pitch/jitter/shimmer measurements via
  [Parselmouth](https://parselmouth.readthedocs.io/) (Python bindings for
  Praat), computed over a rolling audio buffer per speaker slot. Voice stress
  analysis as a lie-detector is pseudoscience, to be clear -- but the
  underlying acoustic numbers feeding the meter are real, not decorative.
  With only one mic, "two voices" means the operator toggles which speaker
  slot is currently recording (keys `1`/`2`) -- there's no real diarization.
- **Playback**: every live frame is pushed into a rolling ring buffer
  regardless of state; saying "playback" freezes the feed and loops that
  buffer until another command is heard.
- One shared `sounddevice` input stream feeds both the voice-command
  listener and the stress analyzer, so they don't fight over the mic.

## Setup

```powershell
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python scripts\download_model.py   # ~40MB, one-time
venv\Scripts\python -m robo_view.main
```

Uses webcam index 0 and the system default microphone by default -- see
`robo_view/config.py` to change either, along with tracker box size, HUD
colors, playback length, etc.
