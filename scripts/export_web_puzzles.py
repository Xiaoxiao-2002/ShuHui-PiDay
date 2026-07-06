from __future__ import annotations

import json
from pathlib import Path

from shuhui.web_export import export_web_bundle


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    catalog = json.loads((ROOT / "web" / "puzzle-catalog.json").read_text(encoding="utf-8"))
    entries = catalog["entries"]
    paths = [ROOT / entry["source"] for entry in entries]
    items = export_web_bundle(
        paths,
        ROOT / "web" / "public" / "puzzles",
        catalog_entries=entries,
        catalog_version=catalog["catalogVersion"],
    )
    print(f"已导出 {len(items)} 道网页题目，未包含答案字段。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
