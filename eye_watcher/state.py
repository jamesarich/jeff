from enum import Enum, auto


class VisitorState(Enum):
    IDLE = auto()
    WATCHING = auto()


class VisitorStateMachine:
    def __init__(self, cooldown_seconds: float = 60.0):
        self.cooldown_seconds = cooldown_seconds
        self.state = VisitorState.IDLE
        self._last_trigger_time: float | None = None

    def update(self, face_found: bool, now: float) -> bool:
        triggered = False
        if face_found:
            if self.state is VisitorState.IDLE:
                cooldown_elapsed = (
                    self._last_trigger_time is None
                    or (now - self._last_trigger_time) >= self.cooldown_seconds
                )
                if cooldown_elapsed:
                    triggered = True
                    self._last_trigger_time = now
            self.state = VisitorState.WATCHING
        else:
            self.state = VisitorState.IDLE
        return triggered
