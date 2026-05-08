# ================================================================
# ANIMATION
# Frame loading, sprite mirroring, animation state machine.
# Used by the Pet widget in pet.py.
# ================================================================

import os
import random
import time

from PyQt5.QtGui import QPixmap, QTransform


def load_frames(base_path: str, folder: str) -> list:
    """Load all PNG frames from a subfolder, sorted by filename."""
    frames = []
    folder_path = os.path.join(base_path, folder)
    if not os.path.exists(folder_path):
        print(f"[animation] folder not found: {folder_path}")
        return frames
    for file in sorted(f for f in os.listdir(folder_path) if f.endswith(".png")):
        frames.append(QPixmap(os.path.join(folder_path, file)))
    return frames


def mirror_frame(pixmap: QPixmap) -> QPixmap:
    """Flip a QPixmap horizontally."""
    return pixmap.transformed(QTransform().scale(-1, 1))


class AnimationController:
    """
    Manages the pet's animation state:
      idle → click (one-shot) → idle
      idle → sleep (after timeout) → idle (on interaction)
    """

    SLEEP_AFTER = 10  # seconds of inactivity before sleeping

    def __init__(self, idle_frames, click_frames, sleep_frames):
        self.idle_frames  = idle_frames
        self.click_frames = click_frames
        self.sleep_frames = sleep_frames

        self.current_frames = idle_frames
        self.frame_index    = 0
        self.playing_click  = False
        self.sleeping       = False
        self._last_active   = time.time()
        self._facing_right  = True  # True = original, False = mirrored

    # ----------------------------------------------------------------
    # Direction / mirroring
    # ----------------------------------------------------------------
    def update_direction(self, pet_center_x: int, screen_mid_x: int):
        """Flip sprite depending on which half of the screen the pet is on."""
        facing_right = pet_center_x >= screen_mid_x
        if facing_right != self._facing_right:
            self._facing_right = facing_right
            self.frame_index = 0  # reset to avoid jump

    def current_pixmap(self) -> QPixmap:
        """Return the current frame, mirrored if needed."""
        if not self.current_frames:
            return QPixmap()
        px = self.current_frames[self.frame_index]
        return px if self._facing_right else mirror_frame(px)

    # ----------------------------------------------------------------
    # Tick — called by QTimer (~30 fps)
    # ----------------------------------------------------------------
    def tick(self):
        """Advance animation by one frame. Returns the pixmap to display."""
        if not self.current_frames:
            return None

        # Auto-sleep after inactivity
        if not self.sleeping and time.time() - self._last_active > self.SLEEP_AFTER:
            self._start_sleep()

        px = self.current_pixmap()

        self.frame_index += 1
        if self.frame_index >= len(self.current_frames):
            self.frame_index = 0
            if self.playing_click:
                # Click animation finished → back to idle
                self.playing_click  = False
                self.current_frames = self.idle_frames

        return px

    # ----------------------------------------------------------------
    # State transitions
    # ----------------------------------------------------------------
    def play_click(self):
        if self.click_frames:
            self.current_frames = self.click_frames
            self.frame_index    = 0
            self.playing_click  = True
            self.sleeping       = False
        self._last_active = time.time()

    def _start_sleep(self):
        if self.sleep_frames:
            self.current_frames = self.sleep_frames
            self.frame_index    = 0
            self.sleeping       = True
            self.playing_click  = False

    def wake_up(self):
        self.sleeping       = False
        self.current_frames = self.idle_frames
        self.frame_index    = 0
        self._last_active   = time.time()

    def poke(self):
        """Register user interaction (drag, click)."""
        self._last_active = time.time()

    def random_behavior(self) -> int:
        """Randomly play click animation. Returns next interval in ms."""
        if not self.sleeping and random.random() < 0.3:
            self.play_click()
        return random.randint(3000, 6000)
