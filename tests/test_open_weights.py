import importlib.util

from app.config import ROOT

spec = importlib.util.spec_from_file_location("check_open_weights", ROOT / "scripts" / "check_open_weights.py")
cow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cow)


def test_shipped_workflows_contain_no_partner_nodes():
    assert cow.check_dir() == {}


def test_checker_flags_partner_nodes():
    g = {"1": {"class_type": "KlingImage2VideoNode", "inputs": {}}, "2": {"class_type": "OpenAIChatNode", "inputs": {}}, "3": {"class_type": "KSampler", "inputs": {}}, "4": {"class_type": "LTXVImgToVideoInplace", "inputs": {}}}
    assert cow.check_graph(g) == ["KlingImage2VideoNode", "OpenAIChatNode"]


def test_workflows_are_marked_untested_and_inputs_exist():
    import json
    for stem in ("ltx2_i2v_camera", "qwen_edit_angle"):
        graph = json.loads((ROOT / "workflows" / f"{stem}.json").read_text())
        meta = json.loads((ROOT / "workflows" / f"{stem}.meta.json").read_text())
        assert "untested" in meta["status"].lower()
        assert meta["output_node"] in graph
        for key, targets in meta["inputs"].items():
            for node_id, field in targets:
                assert node_id in graph, (stem, key)
                assert field in graph[node_id]["inputs"], (stem, key, node_id, field)


def test_official_ltx23_template_is_valid_json_ui_format_without_partner_nodes():
    import json
    p = ROOT / "workflows" / "ltx23_i2v_official_template.json"
    g = json.loads(p.read_text())
    types = cow.node_types(g)
    assert {"LoadImage", "SaveVideo", "LTXVImgToVideoInplace", "LTXVLatentUpsampler"} <= set(types)
    assert cow.check_graph(g) == []
    assert (ROOT / "workflows" / "ltx23_i2v_official_template.NOTICE.md").read_text().count("MIT") >= 1


def test_checker_descends_into_subgraphs_of_ui_format():
    g = {"nodes": [{"type": "uuid-1"}, {"type": "SaveVideo"}],
         "definitions": {"subgraphs": [{"id": "uuid-1", "nodes": [{"type": "KlingImage2VideoNode"}, {"type": "KSampler"}]}]}}
    assert cow.node_types(g) == {"SaveVideo": 1, "KlingImage2VideoNode": 1, "KSampler": 1}
    assert cow.check_graph(g) == ["KlingImage2VideoNode"]
