"""RoboCop-calibration-scene, built out of a webcam + a bit of nostalgia.

Flow (all voice-triggered, say the word out loud):
  "grid"      -> draw the targeting grid + center crosshair
  "target"    -> click on something in the video window to lock onto it
  "follow"    -> keep tracking that target continuously (needs a target first)
  "stress"    -> voice stress analyzer; press 1/2 to say who's talking
  "playback"  -> replay the last few seconds on a loop
  "reset"     -> back to idle

Keys: 1/2 pick the active speaker in stress mode, q/ESC quits.
"""

import collections

import cv2

from . import config as cfg
from . import hud
from .audio_hub import AudioHub
from .playback import FrameRingBuffer, PlaybackController
from .stress import VoiceStressAnalyzer
from .tracker import PenTracker
from .voice_commands import VoiceCommandListener

STATE_IDLE = "IDLE"
STATE_GRID = "GRID"
STATE_TARGET_WAIT = "TARGET_WAIT"
STATE_TARGET = "TARGET"
STATE_FOLLOW = "FOLLOW"
STATE_STRESS = "STRESS"
STATE_PLAYBACK = "PLAYBACK"

WINDOW_NAME = "ROBO VIEW"


class App:
    def __init__(self):
        # cv2's default MSMF backend on Windows is known to hang for several
        # seconds (sometimes indefinitely) on some webcams; DirectShow opens
        # reliably for the vast majority of USB cams.
        self.cap = cv2.VideoCapture(cfg.CAMERA_INDEX, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.FRAME_HEIGHT)
        if not self.cap.isOpened():
            raise RuntimeError("Could not open webcam (index %d)" % cfg.CAMERA_INDEX)

        self.audio_hub = AudioHub()
        self.voice = VoiceCommandListener(self.audio_hub)
        self.stress = VoiceStressAnalyzer(self.audio_hub)
        self.tracker = PenTracker()
        self.ring_buffer = FrameRingBuffer()
        self.playback = PlaybackController()

        self.state = STATE_IDLE
        self.last_heard = ""
        self.click_point = None
        self.smoothed_center = None
        self.trail = collections.deque(maxlen=20)

        cv2.namedWindow(WINDOW_NAME)
        cv2.setMouseCallback(WINDOW_NAME, self._on_mouse)

    # -- input handling -----------------------------------------------------

    def _on_mouse(self, event, x, y, flags, userdata):
        if event == cv2.EVENT_LBUTTONDOWN and self.state == STATE_TARGET_WAIT:
            self.click_point = (x, y)

    def _handle_command(self, command):
        if command == "grid":
            self.state = STATE_GRID
        elif command == "target":
            self.state = STATE_TARGET_WAIT
        elif command == "follow":
            self.state = STATE_FOLLOW if self.tracker.active else STATE_TARGET_WAIT
        elif command == "stress":
            self.state = STATE_STRESS
        elif command == "playback":
            frames = self.ring_buffer.snapshot()
            self.playback.start(frames)
            self.state = STATE_PLAYBACK
        elif command == "reset":
            self.tracker.reset()
            self.playback.stop()
            self.state = STATE_IDLE

        self.stress.enabled = self.state == STATE_STRESS

    def _handle_key(self, key):
        if key in (ord("1"),):
            self.stress.active_speaker = 1
        elif key in (ord("2"),):
            self.stress.active_speaker = 2
        # Debug fallback -- voice is the primary interface, but these make it
        # possible to drive the demo when the mic isn't cooperating.
        elif key == ord("g"):
            self._handle_command("grid")
        elif key == ord("t"):
            self._handle_command("target")
        elif key == ord("f"):
            self._handle_command("follow")
        elif key == ord("s"):
            self._handle_command("stress")
        elif key == ord("p"):
            self._handle_command("playback")
        elif key == ord("r"):
            self._handle_command("reset")

    # -- per-state rendering --------------------------------------------------

    def _render_idle(self, frame):
        hud.draw_hud_text(frame, ["SYSTEM READY", "SAY \"GRID\" TO BEGIN CALIBRATION"])

    def _render_grid(self, frame):
        h, w = frame.shape[:2]
        hud.draw_grid(frame)
        hud.draw_crosshair(frame, (w // 2, h // 2))
        hud.draw_hud_text(frame, ["GRID"])

    def _render_target_wait(self, frame):
        hud.draw_hud_text(frame, ["CLICK THE TARGET TO LOCK ON"])

    def _render_target(self, frame):
        ok, bbox, center = self.tracker.update(frame)
        if ok:
            hud.draw_lock_brackets(frame, bbox, label="TARGET")
            hud.draw_crosshair(frame, center, size=30)
        else:
            hud.draw_hud_text(frame, ["TARGET LOST - SAY \"TARGET\" TO REACQUIRE"], color=cfg.COLOR_RED)
            self.tracker.reset()
            self.state = STATE_TARGET_WAIT

    def _render_follow(self, frame):
        ok, bbox, center = self.tracker.update(frame)
        if not ok:
            hud.draw_hud_text(frame, ["TARGET LOST - SAY \"TARGET\" TO REACQUIRE"], color=cfg.COLOR_RED)
            self.tracker.reset()
            self.state = STATE_TARGET_WAIT
            return

        if self.smoothed_center is None:
            self.smoothed_center = center
        else:
            a = cfg.FOLLOW_SMOOTHING
            self.smoothed_center = (
                self.smoothed_center[0] * a + center[0] * (1 - a),
                self.smoothed_center[1] * a + center[1] * (1 - a),
            )
        self.trail.append(self.smoothed_center)

        for i in range(1, len(self.trail)):
            cv2.line(frame, (int(self.trail[i - 1][0]), int(self.trail[i - 1][1])),
                      (int(self.trail[i][0]), int(self.trail[i][1])), cfg.COLOR_DIM_GREEN, 1, cv2.LINE_AA)

        hud.draw_lock_brackets(frame, bbox, label="FOLLOWING")
        hud.draw_crosshair(frame, self.smoothed_center, size=30)

    def _render_stress(self, frame):
        results = self.stress.maybe_analyze()
        h, w = frame.shape[:2]
        hud.draw_hud_text(frame, ["VOICE STRESS ANALYZER", "PRESS 1 / 2 TO SELECT ACTIVE SPEAKER"])

        for speaker, x in ((1, 40), (2, w // 2 + 40)):
            active = self.stress.active_speaker == speaker
            color = cfg.COLOR_GREEN if active else cfg.COLOR_DIM_GREEN
            label = f"VOICE {speaker}" + (" (LISTENING)" if active else "")
            data = results.get(speaker)
            stress_val = data["stress"] if data else 0
            f0 = data["f0_mean"] if data else 0
            jitter = data["jitter"] if data else 0
            hud.draw_meter(frame, (x, h - 160), 260, 24, stress_val, 100, f"{label} STRESS", color)
            hud.draw_hud_text(frame, [f"F0: {f0:5.1f} Hz", f"JITTER: {jitter*100:4.2f}%"],
                               origin=(x, h - 110), color=color, scale=0.5, line_gap=22)

    def _render_playback(self, frame_unused):
        frame = self.playback.next_frame()
        if frame is None:
            hud.draw_hud_text(frame_unused, ["NOTHING BUFFERED YET"], color=cfg.COLOR_RED)
            return frame_unused
        hud.draw_hud_text(frame, [f"PLAYBACK - LAST {cfg.PLAYBACK_SECONDS}s"], color=cfg.COLOR_AMBER)
        hud.draw_meter(frame, (20, frame.shape[0] - 40), 300, 10, self.playback.progress, 1.0,
                        "", cfg.COLOR_AMBER)
        return frame

    # -- main loop ------------------------------------------------------------

    def run(self):
        self.audio_hub.start()
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break
                self.ring_buffer.push(frame)

                heard = self.voice.poll()
                if heard:
                    command, text = heard
                    self.last_heard = text
                    self._handle_command(command)

                if self.state == STATE_TARGET_WAIT and self.click_point is not None:
                    self.tracker.acquire(frame, self.click_point)
                    self.click_point = None
                    self.state = STATE_TARGET
                    self.smoothed_center = None
                    self.trail.clear()

                display = frame
                if self.state == STATE_IDLE:
                    self._render_idle(display)
                elif self.state == STATE_GRID:
                    self._render_grid(display)
                elif self.state == STATE_TARGET_WAIT:
                    self._render_target_wait(display)
                elif self.state == STATE_TARGET:
                    self._render_target(display)
                elif self.state == STATE_FOLLOW:
                    self._render_follow(display)
                elif self.state == STATE_STRESS:
                    self._render_stress(display)
                elif self.state == STATE_PLAYBACK:
                    display = self._render_playback(display)

                hud.draw_state_banner(display, f"[{self.state}]  heard: {self.last_heard}")
                cv2.imshow(WINDOW_NAME, display)

                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                self._handle_key(key)
        finally:
            self.cleanup()

    def cleanup(self):
        self.audio_hub.stop()
        self.cap.release()
        cv2.destroyAllWindows()


def main():
    App().run()


if __name__ == "__main__":
    main()
