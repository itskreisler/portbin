import json
from pathlib import Path

MANIFESTS_DIR = Path(__file__).resolve().parent.parent / "manifests"


def test_all_manifests_valid_json():
    json_files = list(MANIFESTS_DIR.glob("*.json"))
    assert len(json_files) >= 15
    for file in json_files:
        with file.open(encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict)
            if file.name != "index.json":
                assert "tool" in data
                assert "steps" in data
                assert isinstance(data["steps"], list)


def test_index_json_contains_all_tools():
    index_file = MANIFESTS_DIR / "index.json"
    assert index_file.exists()
    with index_file.open(encoding="utf-8") as f:
        data = json.load(f)
    tools_in_index = data.get("tools", {})
    manifest_files = [f.stem for f in MANIFESTS_DIR.glob("*.json") if f.name != "index.json"]
    assert "index" not in tools_in_index
    for tool in manifest_files:
        assert tool in tools_in_index
