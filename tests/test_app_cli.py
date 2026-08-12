from eye_watcher.app import parse_args


def test_parse_args_defaults():
    args = parse_args([])
    assert args.fullscreen is False
    assert args.debug is False
    assert args.camera_index == 0
    assert args.cooldown == 60.0
    assert args.smoothing_alpha == 0.3
    assert args.fps == 15.0
    assert args.mirror is True


def test_parse_args_no_mirror():
    args = parse_args(["--no-mirror"])
    assert args.mirror is False


def test_parse_args_default_paths_are_absolute():
    args = parse_args([])
    assert args.image.is_absolute()
    assert args.calibration.is_absolute()
    assert args.sounds_dir.is_absolute()


def test_parse_args_overrides():
    args = parse_args(["--fullscreen", "--debug", "--camera-index", "2", "--cooldown", "10"])
    assert args.fullscreen is True
    assert args.debug is True
    assert args.camera_index == 2
    assert args.cooldown == 10.0
