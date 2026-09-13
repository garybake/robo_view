"""Drawing helpers for the targeting-computer look: crosshairs, grids,
lock-on brackets and HUD text panels. Nothing here reads state, it just
paints what it's told onto a frame in place.
"""

import cv2

from . import config as cfg


def draw_grid(frame, spacing=64, color=cfg.COLOR_DIM_GREEN, thickness=1):
    h, w = frame.shape[:2]
    for x in range(0, w, spacing):
        cv2.line(frame, (x, 0), (x, h), color, thickness, cv2.LINE_AA)
    for y in range(0, h, spacing):
        cv2.line(frame, (0, y), (w, y), color, thickness, cv2.LINE_AA)


def draw_crosshair(frame, center, size=40, color=cfg.COLOR_GREEN, thickness=2, gap=8):
    x, y = int(center[0]), int(center[1])
    cv2.line(frame, (x - size, y), (x - gap, y), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x + gap, y), (x + size, y), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x, y - size), (x, y - gap), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x, y + gap), (x, y + size), color, thickness, cv2.LINE_AA)
    cv2.circle(frame, (x, y), 3, color, -1, cv2.LINE_AA)
    cv2.circle(frame, (x, y), size, color, 1, cv2.LINE_AA)


def draw_lock_brackets(frame, bbox, color=cfg.COLOR_GREEN, thickness=2, label=None):
    """RoboCop/military HUD style corner brackets around a tracked box."""
    x, y, w, h = [int(v) for v in bbox]
    arm = max(10, min(w, h) // 4)

    corners = [(x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)]
    for cx, cy, dx, dy in corners:
        cv2.line(frame, (cx, cy), (cx + dx * arm, cy), color, thickness, cv2.LINE_AA)
        cv2.line(frame, (cx, cy), (cx, cy + dy * arm), color, thickness, cv2.LINE_AA)

    if label:
        cv2.putText(frame, label, (x, max(0, y - 10)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, color, 1, cv2.LINE_AA)


def draw_hud_text(frame, lines, origin=(20, 30), color=cfg.COLOR_GREEN, scale=0.6, line_gap=26):
    x, y = origin
    for i, line in enumerate(lines):
        cv2.putText(frame, line, (x, y + i * line_gap), cv2.FONT_HERSHEY_SIMPLEX,
                    scale, color, 1, cv2.LINE_AA)


def draw_state_banner(frame, text, color=cfg.COLOR_GREEN):
    h, w = frame.shape[:2]
    cv2.putText(frame, text, (w // 2 - 140, h - 24), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, color, 2, cv2.LINE_AA)


def draw_meter(frame, top_left, width, height, value, max_value, label, color=cfg.COLOR_GREEN):
    """Horizontal bar meter, value in [0, max_value]."""
    x, y = top_left
    cv2.rectangle(frame, (x, y), (x + width, y + height), color, 1, cv2.LINE_AA)
    frac = 0 if max_value <= 0 else max(0.0, min(1.0, value / max_value))
    fill_w = int(width * frac)
    if fill_w > 0:
        cv2.rectangle(frame, (x, y), (x + fill_w, y + height), color, -1, cv2.LINE_AA)
    cv2.putText(frame, label, (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)


def draw_vignette_scanline(frame, alpha=0.08):
    """Subtle horizontal scanlines for a CRT/targeting-computer feel."""
    h = frame.shape[0]
    overlay = frame.copy()
    for y in range(0, h, 3):
        cv2.line(overlay, (0, y), (frame.shape[1], y), (0, 0, 0), 1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, dst=frame)
