from __future__ import annotations

from pathlib import Path

from shuhui.web_export import export_web_bundle


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    paths = sorted((ROOT / "output" / "puzzles").glob("*/*.json"), key=lambda path: int(path.stem))
    items = export_web_bundle(paths, ROOT / "web" / "public" / "puzzles")
    print(f"已导出 {len(items)} 道网页题目，未包含答案字段。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
