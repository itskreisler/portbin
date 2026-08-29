import json
from pathlib import Path

MANIFESTS_DIR = Path(__file__).resolve().parent.parent / "manifests"


def test_all_manifests_valid_json():
    json_files = list(MANIFESTS_DIR.rglob("*.json"))
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
    manifest_tools = {
        p.relative_to(MANIFESTS_DIR).parts[0] if len(p.relative_to(MANIFESTS_DIR).parts) > 1 else p.stem
        for p in MANIFESTS_DIR.rglob("*.json")
        if p.name != "index.json"
    }
    assert "index" not in tools_in_index
    for tool in manifest_tools:
        assert tool in tools_in_index
