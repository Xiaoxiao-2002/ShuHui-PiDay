import json
import stat

from shuhui.web_export import export_web_bundle


def test_web_export_contains_twenty_sanitized_unique_puzzles(tmp_path):
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    paths = sorted((root / "output" / "puzzles").glob("*/*.json"), key=lambda path: int(path.stem))
    items = export_web_bundle(paths, tmp_path)
    assert [item["id"] for item in items] == [f"TSH-{index:02d}" for index in range(1, 21)]
    for item in items:
        exported = tmp_path / item["file"]
        text = exported.read_text(encoding="utf-8")
        payload = json.loads(text)
        assert "target_solution_edges" not in text
        assert "solution_edges" not in text
        assert "analysis" not in payload
        assert payload["topology"]["edges"]
        assert exported.stat().st_mode & stat.S_IROTH
