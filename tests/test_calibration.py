from eye_watcher.calibration import Calibration, EyeCalibration, save_calibration, load_calibration


def test_save_and_load_round_trip(tmp_path):
    cal = Calibration(
        left=EyeCalibration(center_x=100.0, center_y=200.0, radius=15.0),
        right=EyeCalibration(center_x=180.0, center_y=200.0, radius=15.0),
    )
    path = tmp_path / "calibration.json"

    save_calibration(path, cal)
    loaded = load_calibration(path)

    assert loaded == cal
