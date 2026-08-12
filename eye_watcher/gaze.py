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


def largest_face(faces):
    """Pick the face landmark list with the largest bounding-box area."""
    if len(faces) == 1:
        return faces[0]

    def area(landmarks) -> float:
        min_x = max_x = landmarks[0].x
        min_y = max_y = landmarks[0].y
        for point in landmarks[1:]:
            if point.x < min_x:
                min_x = point.x
            elif point.x > max_x:
                max_x = point.x
            if point.y < min_y:
                min_y = point.y
            elif point.y > max_y:
                max_y = point.y
        return (max_x - min_x) * (max_y - min_y)

    return max(faces, key=area)
