import random

from eye_watcher.clip_library import ClipLibrary


def test_pick_returns_none_when_folder_empty(tmp_path):
    lib = ClipLibrary(tmp_path)
    assert lib.pick() is None


def test_pick_returns_none_when_folder_missing(tmp_path):
    lib = ClipLibrary(tmp_path / "does-not-exist")
    assert lib.pick() is None


def test_clips_ignores_non_audio_files(tmp_path):
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "clip.wav").write_bytes(b"\x00")
    lib = ClipLibrary(tmp_path)
    assert lib.clips() == [tmp_path / "clip.wav"]


def test_pick_avoids_immediate_repeat(tmp_path):
    (tmp_path / "a.wav").write_bytes(b"\x00")
    (tmp_path / "b.wav").write_bytes(b"\x00")
    lib = ClipLibrary(tmp_path)
    rng = random.Random(0)

    picks = [lib.pick(rng) for _ in range(20)]

    for previous, current in zip(picks, picks[1:]):
        assert previous != current
