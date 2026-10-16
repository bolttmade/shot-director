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


def test_reel_aspects_and_labels():
    clips = [Path("a.mp4"), Path("b.mp4")]
    v = build_command(clips, [5.0, 5.0], Path("o.mp4"), crossfade=0.4, aspect="9:16", labels=["REAL: MiniMax H3 via Comfy Router", "SIMULATED previs"])
    g = _g(v)
    assert "720:1280" in g and "boxblur" in g and g.count("drawtext") == 2 and "overlay" in g
    h = build_command(clips, [5.0, 5.0], Path("o.mp4"), aspect="16:9", labels=["a", "b"])
    assert "1280:720" in _g(h) and _g(h).count("drawtext") == 2 and "concat=n=2" in _g(h)
    assert "drawtext" not in _g(build_command(clips, [5.0, 5.0], Path("o.mp4"), aspect="16:9"))
    with pytest.raises(StitchError):
        build_command(clips, [5.0, 5.0], Path("o.mp4"), aspect="4:3")
    with pytest.raises(StitchError):
        build_command(clips, [5.0, 5.0], Path("o.mp4"), labels=["only one"])


def test_label_text_is_escaped():
    from app.stitch import _esc

    assert "'" not in _esc("it's") and "\\:" in _esc("a:b") and "\\," in _esc("a,b")
