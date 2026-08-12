from dataclasses import dataclass


@dataclass
class FaceOffset:
    dx: float
    dy: float


def landmarks_to_offset(
    point_x: float,
    point_y: float,
    frame_width: int,
    frame_height: int,
    mirror_x: bool = False,
) -> FaceOffset:
    # An unmirrored camera sees a visitor moving to their right as moving toward
    # image-left; mirror_x flips the horizontal axis so the on-screen eyes follow
    # the visitor instead of moving away from them.
    if mirror_x:
        point_x = frame_width - point_x

    center_x = frame_width / 2
    center_y = frame_height / 2

    dx = (point_x - center_x) / center_x
    dy = (point_y - center_y) / center_y

    dx = max(-1.0, min(1.0, dx))
    dy = max(-1.0, min(1.0, dy))

    return FaceOffset(dx=dx, dy=dy)


def largest_face(faces):
    """Pick the face landmark list with the largest bounding-box area."""

    def area(landmarks) -> float:
        xs = [point.x for point in landmarks]
        ys = [point.y for point in landmarks]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))

    return max(faces, key=area)
