from eye_watcher.app import parse_args


def test_parse_args_defaults():
    args = parse_args([])
    assert args.fullscreen is False
    assert args.debug is False
    assert args.camera_index == 0
    assert args.cooldown == 60.0
    assert args.smoothing_alpha == 0.3


def test_parse_args_overrides():
    args = parse_args(["--fullscreen", "--debug", "--camera-index", "2", "--cooldown", "10"])
    assert args.fullscreen is True
    assert args.debug is True
    assert args.camera_index == 2
    assert args.cooldown == 10.0
