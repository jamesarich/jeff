from eye_watcher.state import VisitorState, VisitorStateMachine


def test_no_face_stays_idle_and_never_triggers():
    sm = VisitorStateMachine(cooldown_seconds=60.0)
    assert sm.update(False, 0.0) is False
    assert sm.state is VisitorState.IDLE


def test_first_detection_triggers_and_enters_watching():
    sm = VisitorStateMachine(cooldown_seconds=60.0)
    sm.update(False, 0.0)
    assert sm.update(True, 1.0) is True
    assert sm.state is VisitorState.WATCHING


def test_continued_presence_does_not_retrigger():
    sm = VisitorStateMachine(cooldown_seconds=60.0)
    sm.update(True, 1.0)
    assert sm.update(True, 2.0) is False
    assert sm.update(True, 3.0) is False


def test_leaving_and_returning_within_cooldown_does_not_retrigger():
    sm = VisitorStateMachine(cooldown_seconds=60.0)
    sm.update(True, 1.0)          # triggers, last_trigger_time = 1.0
    sm.update(False, 2.0)         # leaves frame -> IDLE
    assert sm.update(True, 10.0) is False   # 10 - 1 = 9s < 60s cooldown
    assert sm.state is VisitorState.WATCHING


def test_leaving_and_returning_after_cooldown_retriggers():
    sm = VisitorStateMachine(cooldown_seconds=60.0)
    sm.update(True, 1.0)          # triggers, last_trigger_time = 1.0
    sm.update(False, 2.0)         # leaves frame -> IDLE
    assert sm.update(True, 70.0) is True    # 70 - 1 = 69s >= 60s cooldown
