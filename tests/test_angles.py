from app import angles
from app.types import Angle


def test_snap_to_training_grid():
    s = angles.snap_angle(Angle(50, 20, "close"))
    assert (s.azimuth, s.elevation, s.distance) == (45, 30, "close")
    assert angles.snap_angle(Angle(-10, -100, "bogus")).distance == "medium"
    assert angles.snap_angle(Angle(359, 0)).azimuth == 0


def test_qwen_prompt_vocabulary():
    assert angles.qwen_prompt(Angle(0, 0, "medium")) == "<sks> front view eye-level shot medium shot"
    assert angles.qwen_prompt(Angle(90, 60, "wide")) == "<sks> right side view high-angle shot wide shot"
    assert angles.qwen_prompt(Angle(-90, -30, "close")).startswith("<sks> left side view low-angle shot")


def test_coverage_is_six_distinct_shots():
    assert len(angles.COVERAGE) == 6
    assert len({angles.qwen_prompt(c["angle"]) for c in angles.COVERAGE}) == 6


def test_demo_camera_pose_is_clamped():
    cam = angles.angle_to_cam(Angle(180, 0))
    assert abs(cam["right"]) <= 1.0  # a single still cannot show the back of a subject
