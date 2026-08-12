from enum import Enum, auto


class VisitorState(Enum):
    IDLE = auto()
    WATCHING = auto()


class VisitorStateMachine:
    def __init__(self, cooldown_seconds: float = 60.0, lost_grace_seconds: float = 2.0):
        self.cooldown_seconds = cooldown_seconds
        # Detection flickers (a single missed frame) must not count as the
        # visitor leaving, or the greeting re-triggers at the same person.
        self.lost_grace_seconds = lost_grace_seconds
        self.state = VisitorState.IDLE
        self._last_trigger_time: float | None = None
        self._last_seen_time: float | None = None

    def update(self, face_found: bool, now: float) -> bool:
        triggered = False
        if face_found:
            self._last_seen_time = now
            if self.state is VisitorState.IDLE:
                cooldown_elapsed = (
                    self._last_trigger_time is None
                    or (now - self._last_trigger_time) >= self.cooldown_seconds
                )
                if cooldown_elapsed:
                    triggered = True
                    self._last_trigger_time = now
            self.state = VisitorState.WATCHING
        elif self.state is VisitorState.WATCHING:
            face_gone_long_enough = (
                self._last_seen_time is None
                or (now - self._last_seen_time) >= self.lost_grace_seconds
            )
            if face_gone_long_enough:
                self.state = VisitorState.IDLE
        return triggered
