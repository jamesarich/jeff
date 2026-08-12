from dataclasses import dataclass


@dataclass
class FaceOffset:
    dx: float
    dy: float


def landmarks_to_offset(point_x: float, point_y: float, frame_width: int, frame_height: int) -> FaceOffset:
    center_x = frame_width / 2
    center_y = frame_height / 2

    dx = (point_x - center_x) / center_x
    dy = (point_y - center_y) / center_y

    dx = max(-1.0, min(1.0, dx))
    dy = max(-1.0, min(1.0, dy))

    return FaceOffset(dx=dx, dy=dy)
