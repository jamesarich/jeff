# Shared debounce for the noisy per-frame face_found bit: detection flickers
# off for a few frames whenever the visitor moves (motion blur), and neither
# the audio trigger nor the gaze should treat that as the visitor leaving.
FACE_LOST_GRACE_SECONDS = 2.0


class VisitorStateMachine:
    def __init__(
        self,
        cooldown_seconds: float = 60.0,
        lost_grace_seconds: float = FACE_LOST_GRACE_SECONDS,
    ):
        self.cooldown_seconds = cooldown_seconds
        self.lost_grace_seconds = lost_grace_seconds
        self.watching = False
        self._last_trigger_time: float | None = None
        self._last_seen_time: float | None = None

    def update(self, face_found: bool, now: float) -> bool:
        triggered = False
        if face_found:
            self._last_seen_time = now
            if not self.watching:
                cooldown_elapsed = (
                    self._last_trigger_time is None
                    or (now - self._last_trigger_time) >= self.cooldown_seconds
                )
                if cooldown_elapsed:
                    triggered = True
                    self._last_trigger_time = now
            self.watching = True
        elif self.watching:
            face_gone_long_enough = (
                self._last_seen_time is None
                or (now - self._last_seen_time) >= self.lost_grace_seconds
            )
            if face_gone_long_enough:
                self.watching = False
        return triggered
