from pathlib import Path

import pytest

from app.stitch import StitchError, build_command


def _g(cmd):
    return cmd[cmd.index("-filter_complex") + 1]


def test_crossfade_offsets():
    clips = [Path(f"c{i}.mp4") for i in range(3)]
    cmd = build_command(clips, [4.0, 4.0, 4.0], Path("o.mp4"), crossfade=0.4)
    g = _g(cmd)
    assert g.count("xfade") == 2
    assert "offset=3.600" in g and "offset=7.200" in g
    assert cmd[-1] == "o.mp4" and "-an" in cmd


def test_hard_cut_uses_concat():
    cmd = build_command([Path("a.mp4"), Path("b.mp4")], [4, 4], Path("o.mp4"))
    assert "concat=n=2" in _g(cmd)


def test_single_clip_and_empty():
    assert "null[outv]" in _g(build_command([Path("a.mp4")], [4], Path("o.mp4"), crossfade=0.4))
    with pytest.raises(StitchError):
        build_command([], [], Path("o.mp4"))
