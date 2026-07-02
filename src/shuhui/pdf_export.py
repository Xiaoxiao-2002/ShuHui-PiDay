from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .difficulty import difficulty_display, difficulty_tier
from .model import ClueKind, Puzzle
from .topology import Topology, build_topology


def _register_chinese_font() -> str:
    candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/msyh.ttc",
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/simhei.ttf",
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    ]
    for path in candidates:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont("ShuhuiCJK", str(path)))
                return "ShuhuiCJK"
            except Exception:
                continue
    return "Helvetica"


FONT_NAME = _register_chinese_font()
PAGE_WIDTH, PAGE_HEIGHT = A4
NAVY = HexColor("#17324D")
INK = HexColor("#17212B")
MUTED = HexColor("#657282")
PAPER = HexColor("#F8F6F1")
CARD = HexColor("#FCFBF8")
GUIDE = HexColor("#D2D8DF")

TIER_STYLE = {
    "beginner": (HexColor("#24745A"), HexColor("#E8F3EE")),
    "medium": (HexColor("#2F6690"), HexColor("#EAF1F7")),
    "difficult": (HexColor("#B45D18"), HexColor("#FFF0E2")),
    "expert": (HexColor("#813C68"), HexColor("#F5E9F1")),
}


def _puzzle_tier(puzzle: Puzzle) -> str:
    tier = puzzle.metadata.get("difficulty_tier")
    if tier in TIER_STYLE:
        return str(tier)
    level = puzzle.metadata.get("difficulty_level")
    if isinstance(level, int):
        return difficulty_tier(level)
    label = str(puzzle.metadata.get("curated_difficulty", "")).lower()
    legacy = {"1 级": "beginner", "2 级": "beginner", "3 级": "medium", "4 级": "difficult", "5 级": "expert"}
    for old, mapped in legacy.items():
        if old in label:
            return mapped
    for candidate in TIER_STYLE:
        if candidate in label:
            return candidate
    return "beginner"


def _draw_board(
    pdf: canvas.Canvas,
    puzzle: Puzzle,
    topology: Topology,
    box: tuple[float, float, float, float],
    solution_edges: Sequence[str] | None,
    *,
    solution_color=NAVY,
) -> None:
    left, bottom, width, height = box
    xs = [vertex.x for vertex in topology.vertices.values()]
    ys = [vertex.y for vertex in topology.vertices.values()]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    span_x, span_y = max(1e-6, max_x - min_x), max(1e-6, max_y - min_y)
    scale = min(width / span_x, height / span_y)
    ox = left + (width - span_x * scale) / 2 - min_x * scale
    oy = bottom + (height - span_y * scale) / 2 + max_y * scale
    tx = lambda x: ox + x * scale
    ty = lambda y: oy - y * scale

    def draw_edge(edge_id: str, color, line_width: float, dashed: bool) -> None:
        edge = topology.edges[edge_id]
        pdf.setStrokeColor(color)
        pdf.setLineWidth(line_width)
        pdf.setLineCap(1)
        pdf.setDash(2.0, 2.0) if dashed else pdf.setDash()
        if edge.circle_center is None:
            a, b = (topology.vertices[vertex_id] for vertex_id in edge.vertices)
            pdf.line(tx(a.x), ty(a.y), tx(b.x), ty(b.y))
        else:
            cx, cy = edge.circle_center
            radius = (edge.circle_radius or 0.5) * scale
            # ReportLab uses counter-clockwise angles; the model's y axis points down.
            pdf.arc(
                tx(cx) - radius,
                ty(cy) - radius,
                tx(cx) + radius,
                ty(cy) + radius,
                -(edge.start_angle or 0),
                -(edge.span_angle or 60),
            )

    # Candidate arcs are deliberately pale and dashed: pencil and black pen
    # remain visually dominant on an ordinary office printer.
    for edge_id in topology.edges:
        draw_edge(edge_id, GUIDE, 0.65, True)
    for edge_id in solution_edges or []:
        draw_edge(edge_id, solution_color, 2.8, False)
    pdf.setDash()

    clues = puzzle.clue_map()
    font_size = max(8.5, min(17, scale * 0.22))
    pdf.setFont(FONT_NAME, font_size)
    pdf.setFillColor(INK)
    for cell_id, clue in clues.items():
        x, y = topology.cells[cell_id].center
        text = "π" if clue.kind == ClueKind.PI else str(clue.value)
        pdf.drawCentredString(tx(x), ty(y) - font_size * 0.34, text)


def _pill(pdf: canvas.Canvas, x: float, y: float, text: str, tier: str) -> None:
    accent, pale = TIER_STYLE[tier]
    width = max(112, pdfmetrics.stringWidth(text, FONT_NAME, 9) + 24)
    pdf.setFillColor(pale)
    pdf.roundRect(x - width, y - 11, width, 24, 12, stroke=0, fill=1)
    pdf.setFillColor(accent)
    pdf.setFont(FONT_NAME, 9)
    pdf.drawCentredString(x - width / 2, y - 3, text)


def _page_header(pdf: canvas.Canvas, puzzle: Puzzle, index: int, *, answers: bool) -> str:
    tier = _puzzle_tier(puzzle)
    accent, _ = TIER_STYLE[tier]
    puzzle_id = str(puzzle.metadata.get("id", f"TSH-{index:02d}"))

    pdf.setFillColor(PAPER)
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
    pdf.setFillColor(accent)
    pdf.rect(0, PAGE_HEIGHT - 9, PAGE_WIDTH, 9, stroke=0, fill=1)
    pdf.setFillColor(MUTED)
    pdf.setFont(FONT_NAME, 8)
    pdf.drawString(34, PAGE_HEIGHT - 35, "πDay - 特色数回")
    pdf.setStrokeColor(HexColor("#D9DDE1"))
    pdf.setLineWidth(0.6)
    pdf.line(34, PAGE_HEIGHT - 45, PAGE_WIDTH - 34, PAGE_HEIGHT - 45)

    pdf.setFillColor(INK)
    pdf.setFont(FONT_NAME, 23)
    pdf.drawString(34, PAGE_HEIGHT - 82, puzzle_id)
    _pill(pdf, PAGE_WIDTH - 34, PAGE_HEIGHT - 76, difficulty_display(tier), tier)
    return tier


def _info_panel(pdf: canvas.Canvas, puzzle: Puzzle, *, answers: bool, tier: str) -> None:
    accent, pale = TIER_STYLE[tier]
    y = PAGE_HEIGHT - 149
    if answers:
        numbers = sum(clue.kind == ClueKind.NUMBER for clue in puzzle.clues)
        pis = sum(clue.kind == ClueKind.PI for clue in puzzle.clues)
        info = f"数字提示 {numbers}    π 提示 {pis}"
        pdf.setFillColor(pale)
        pdf.roundRect(34, y, PAGE_WIDTH - 68, 34, 8, stroke=0, fill=1)
        pdf.setFillColor(accent)
        pdf.setFont(FONT_NAME, 9)
        pdf.drawString(47, y + 12, "深色实线为唯一解")
        pdf.setFillColor(MUTED)
        pdf.drawRightString(PAGE_WIDTH - 47, y + 12, info)
    else:
        pdf.setFillColor(pale)
        pdf.roundRect(34, y, PAGE_WIDTH - 68, 34, 8, stroke=0, fill=1)
        pdf.setFillColor(accent)
        pdf.setFont(FONT_NAME, 9)
        pdf.drawString(47, y + 12, "沿浅灰虚线描出一条不交叉、不分叉的单一闭环；可用 × 标记排除边。")


def _footer(pdf: canvas.Canvas, page_number: int, page_total: int | None = None, *, answers: bool = False) -> None:
    pdf.setStrokeColor(HexColor("#D9DDE1"))
    pdf.setLineWidth(0.5)
    pdf.line(34, 34, PAGE_WIDTH - 34, 34)
    pdf.setFillColor(MUTED)
    pdf.setFont(FONT_NAME, 7.5)
    pdf.drawString(34, 20, "请保留本页，完成后交给活动工作人员")


def _cover(pdf: canvas.Canvas, *, answers: bool) -> None:
    pdf.setFillColor(PAPER)
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
    pdf.setFillColor(NAVY)
    pdf.rect(0, PAGE_HEIGHT - 292, PAGE_WIDTH, 292, stroke=0, fill=1)

    # A quiet arc motif hints at the circular board without turning the cover
    # into a second puzzle.
    pdf.setStrokeColor(HexColor("#5E7790"))
    pdf.setLineWidth(1.2)
    for cx, cy, radius in ((62, 790, 68), (532, 748, 92), (470, 852, 65), (130, 670, 54)):
        pdf.circle(cx, cy, radius, stroke=1, fill=0)

    pdf.setFillColor(white)
    pdf.setFont(FONT_NAME, 11)
    pdf.drawString(46, PAGE_HEIGHT - 48, "数学文化科普活动")
    pdf.setFont(FONT_NAME, 37)
    pdf.drawString(46, PAGE_HEIGHT - 122, "特色数回")
    pdf.setFont(FONT_NAME, 18)
    pdf.drawString(48, PAGE_HEIGHT - 158, "唯一解答案册" if answers else "纸笔挑战题册")
    pdf.setFont(FONT_NAME, 10)
    pdf.drawString(48, PAGE_HEIGHT - 214, "沿圆弧思考，在密铺的圆之间寻找唯一闭环")

    pdf.setFillColor(INK)
    pdf.setFont(FONT_NAME, 15)
    pdf.drawString(46, PAGE_HEIGHT - 346, "怎么玩")
    rules = [
        "1  沿浅灰虚线描出一条完整闭环，曲线不能交叉或分叉。",
        "2  数字表示闭环经过该单元格边界的弧数。",
        "3  至少与一个 π 单元格相邻的已选圆弧，在六种方向上各有且仅有一条。",
    ]
    pdf.setFont(FONT_NAME, 10.5)
    for row, rule in enumerate(rules):
        pdf.setFillColor(HexColor("#F0ECE4"))
        pdf.roundRect(46, PAGE_HEIGHT - 400 - row * 48, PAGE_WIDTH - 92, 34, 8, stroke=0, fill=1)
        pdf.setFillColor(INK)
        pdf.drawString(60, PAGE_HEIGHT - 388 - row * 48, rule)

    pdf.setFont(FONT_NAME, 15)
    pdf.drawString(46, PAGE_HEIGHT - 548, "四级挑战")
    tiers = ["beginner", "medium", "difficult", "expert"]
    box_width = (PAGE_WIDTH - 110) / 4
    for i, tier in enumerate(tiers):
        accent, pale = TIER_STYLE[tier]
        x = 46 + i * (box_width + 6)
        pdf.setFillColor(pale)
        pdf.roundRect(x, PAGE_HEIGHT - 626, box_width, 52, 8, stroke=0, fill=1)
        pdf.setFillColor(accent)
        pdf.setFont(FONT_NAME, 8.5)
        pdf.drawCentredString(x + box_width / 2, PAGE_HEIGHT - 598, difficulty_display(tier))

    pdf.showPage()


def _rules_page(pdf: canvas.Canvas, examples: Sequence[Puzzle], *, total_pages: int, answers: bool) -> None:
    pdf.setFillColor(PAPER)
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
    pdf.setFillColor(NAVY)
    pdf.rect(0, PAGE_HEIGHT - 9, PAGE_WIDTH, 9, stroke=0, fill=1)
    pdf.setFillColor(MUTED)
    pdf.setFont(FONT_NAME, 8)
    pdf.drawString(34, PAGE_HEIGHT - 35, "πDay - 特色数回")
    pdf.setStrokeColor(HexColor("#D9DDE1"))
    pdf.setLineWidth(0.6)
    pdf.line(34, PAGE_HEIGHT - 45, PAGE_WIDTH - 34, PAGE_HEIGHT - 45)
    pdf.setFillColor(INK)
    pdf.setFont(FONT_NAME, 23)
    pdf.drawString(34, PAGE_HEIGHT - 82, "规则说明")

    rules = [
        ("闭环", "沿候选圆弧画出一条非空的单一闭环；曲线不能交叉、分叉或形成多个小环。"),
        ("数字", "圆和圆隙三角形都是单元格。数字表示闭环经过该单元格边界的弧数；空白格不限。"),
        ("π", "答案曲线中，所有至少与一个 π 单元格相邻的已选圆弧，必须在六种方向上各有且仅有一条。没有 π 时不启用此规则。"),
        ("作答", "沿浅灰虚线描出选中的弧；可在确定不用的弧旁画 ×。下方深色实线表示示例答案。"),
    ]
    y = PAGE_HEIGHT - 122
    for label, text in rules:
        pdf.setFillColor(HexColor("#F0ECE4"))
        pdf.roundRect(34, y - 37, PAGE_WIDTH - 68, 34, 7, stroke=0, fill=1)
        pdf.setFillColor(NAVY)
        pdf.setFont(FONT_NAME, 9)
        pdf.drawString(47, y - 24, label)
        pdf.setFillColor(INK)
        pdf.setFont(FONT_NAME, 8.2)
        pdf.drawString(90, y - 24, text)
        y -= 42

    pdf.setFillColor(INK)
    pdf.setFont(FONT_NAME, 15)
    pdf.drawString(34, 525, "完整示例")
    example_rows = [(examples[0], 300)] if examples else []
    if len(examples) > 1:
        example_rows.append((examples[1], 72))
    for example, bottom in example_rows:
        accent = NAVY
        pale = HexColor("#EEF2F4")
        title = str(example.metadata.get("title", "示例"))
        pdf.setFillColor(INK)
        pdf.setFont(FONT_NAME, 10)
        pdf.drawString(34, bottom + 201, title)
        for x, label, solution in (
            (34, "题目", None),
            (306, "答案", example.analysis.solution_edges or example.target_solution_edges),
        ):
            pdf.setFillColor(pale)
            pdf.roundRect(x, bottom, 255, 188, 9, stroke=0, fill=1)
            pdf.setFillColor(accent)
            pdf.setFont(FONT_NAME, 8)
            pdf.drawString(x + 10, bottom + 170, label)
            topology = build_topology(example)
            _draw_board(pdf, example, topology, (x + 14, bottom + 12, 227, 150), solution, solution_color=accent)
    _footer(pdf, 2, total_pages, answers=answers)
    pdf.showPage()


def _puzzle_page(
    pdf: canvas.Canvas,
    puzzle: Puzzle,
    index: int,
    total_pages: int,
    *,
    answers: bool,
    page_offset: int = 2,
) -> None:
    tier = _page_header(pdf, puzzle, index, answers=answers)
    _info_panel(pdf, puzzle, answers=answers, tier=tier)
    _, pale = TIER_STYLE[tier]
    pdf.setFillColor(CARD)
    pdf.setStrokeColor(HexColor("#DDE1E5"))
    pdf.setLineWidth(0.7)
    pdf.roundRect(34, 54, PAGE_WIDTH - 68, 616, 12, stroke=1, fill=1)
    pdf.setFillColor(pale)
    pdf.roundRect(46, 64, 5, 596, 2.5, stroke=0, fill=1)
    topology = build_topology(puzzle)
    solution = puzzle.analysis.solution_edges or puzzle.target_solution_edges if answers else None
    accent, _ = TIER_STYLE[tier]
    _draw_board(pdf, puzzle, topology, (62, 77, PAGE_WIDTH - 124, 560), solution, solution_color=accent)
    _footer(pdf, index + page_offset, total_pages, answers=answers)
    pdf.showPage()


def export_booklets(
    puzzles: Sequence[Puzzle],
    puzzle_path: str | Path,
    answer_path: str | Path,
    *,
    examples: Sequence[Puzzle] | None = None,
) -> None:
    Path(puzzle_path).parent.mkdir(parents=True, exist_ok=True)
    Path(answer_path).parent.mkdir(parents=True, exist_ok=True)
    puzzle_pdf = canvas.Canvas(str(puzzle_path), pagesize=A4, pageCompression=1)
    answer_pdf = canvas.Canvas(str(answer_path), pagesize=A4, pageCompression=1)
    puzzle_pdf.setTitle("特色数回 · 数学文化挑战题册")
    answer_pdf.setTitle("特色数回 · 答案册")
    _cover(puzzle_pdf, answers=False)
    _cover(answer_pdf, answers=True)
    tier_rank = {"beginner": 0, "medium": 1, "difficult": 2, "expert": 3}

    def order_key(puzzle: Puzzle) -> tuple[int, float, str]:
        difficulty = puzzle.metadata.get("difficulty", {})
        score = float(difficulty.get("score", 0.0)) if isinstance(difficulty, dict) else 0.0
        return tier_rank.get(_puzzle_tier(puzzle), 99), score, str(puzzle.metadata.get("id", ""))

    ordered_puzzles = sorted(puzzles, key=order_key)
    example_puzzles = list(examples or ordered_puzzles[:2])
    total_pages = len(ordered_puzzles) + 2
    _rules_page(puzzle_pdf, example_puzzles, total_pages=total_pages, answers=False)
    _rules_page(answer_pdf, example_puzzles, total_pages=total_pages, answers=True)
    for index, puzzle in enumerate(ordered_puzzles, 1):
        _puzzle_page(puzzle_pdf, puzzle, index, total_pages, answers=False)
        _puzzle_page(answer_pdf, puzzle, index, total_pages, answers=True)
    puzzle_pdf.save()
    answer_pdf.save()


def export_single_pdf(puzzle: Puzzle, path: str | Path, *, show_solution: bool = False) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path), pagesize=A4, pageCompression=1)
    pdf.setTitle(str(puzzle.metadata.get("title", "特色数回")))
    _puzzle_page(pdf, puzzle, 1, 1, answers=show_solution, page_offset=0)
    pdf.save()
