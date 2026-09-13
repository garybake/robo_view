"""Thin wrapper around OpenCV's CSRT tracker: seed it with a click, get a
center point back every frame. This is "target" and "follow" in the movie
scene -- lock onto whatever's under the crosshair when the operator clicks,
then keep reporting where it moved to.
"""

import cv2

from . import config as cfg


class PenTracker:
    def __init__(self):
        self._tracker = None
        self.bbox = None  # (x, y, w, h) in pixel space
        self.ok = False

    @property
    def active(self):
        return self._tracker is not None

    def acquire(self, frame, click_point, box_size=cfg.TARGET_BOX_SIZE):
        """Seed a fresh tracker with a square ROI centered on click_point."""
        h, w = frame.shape[:2]
        cx, cy = click_point
        half = box_size // 2
        x = max(0, min(w - box_size, cx - half))
        y = max(0, min(h - box_size, cy - half))
        bbox = (x, y, box_size, box_size)

        self._tracker = cv2.TrackerCSRT_create()
        self._tracker.init(frame, bbox)
        self.bbox = bbox
        self.ok = True
        return bbox

    def update(self, frame):
        """Advance the tracker one frame. Returns (ok, bbox, center)."""
        if self._tracker is None:
            return False, None, None

        self.ok, bbox = self._tracker.update(frame)
        if self.ok:
            self.bbox = bbox
            x, y, w, h = bbox
            center = (x + w / 2, y + h / 2)
            return True, bbox, center

        return False, self.bbox, None

    def reset(self):
        self._tracker = None
        self.bbox = None
        self.ok = False
