from __future__ import annotations

import copy
import math
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QRectF, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QToolBar,
    QWidget,
)

from .generator import GenerationOptions, generate_puzzle
from .model import Clue, ClueKind, Puzzle, Variant
from .pdf_export import export_single_pdf
from .render import export_svg
from .solver import solve_puzzle, validate_solution_edges, validate_target_solution
from .storage import load_puzzle, save_puzzle
from .topology import Topology, build_topology


class PuzzleCanvas(QWidget):
    cell_selected = Signal(str)
    puzzle_edited = Signal()
    practice_edited = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.puzzle: Puzzle | None = None
        self.topology: Topology | None = None
        self.show_solution = False
        self.edit_target = True
        self.practice_mode = False
        self.practice_edges: set[str] = set()
        self.selected_cell: str | None = None
        self.zoom = 1.0
        self.pan = QPointF(0, 0)
        self._pan_anchor: QPointF | None = None
        self.setAutoFillBackground(True)
        self.setMinimumSize(500, 500)

    def _theme_colors(self) -> dict[str, QColor]:
        dark = self.palette().color(QPalette.Window).lightness() < 128
        if dark:
            return {
                "grid": QColor("#aeb7c4"),
                "target": QColor("#fb923c"),
                "solution": QColor("#60a5fa"),
                "clue": QColor("#f8fafc"),
                "lock": QColor("#f87171"),
                "selection": QColor("#c084fc"),
            }
        return {
            "grid": QColor("#aeb7c4"),
            "target": QColor("#d97706"),
            "solution": QColor("#1859a9"),
            "clue": QColor("#111827"),
            "lock": QColor("#aa2e25"),
            "selection": QColor("#7c3aed"),
        }

    def set_puzzle(self, puzzle: Puzzle) -> None:
        self.puzzle = puzzle
        self.topology = build_topology(puzzle)
        self.selected_cell = None
        self.practice_edges.clear()
        self.zoom = 1.0
        self.pan = QPointF(0, 0)
        self.update()

    def _transform(self):
        assert self.topology
        xs = [v.x for v in self.topology.vertices.values()]
        ys = [v.y for v in self.topology.vertices.values()]
        min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
        span_x, span_y = max(1e-6, max_x - min_x), max(1e-6, max_y - min_y)
        scale = min((self.width() - 70) / span_x, (self.height() - 70) / span_y) * self.zoom
        offset_x = (self.width() - span_x * scale) / 2 - min_x * scale + self.pan.x()
        offset_y = (self.height() - span_y * scale) / 2 - min_y * scale + self.pan.y()
        return scale, offset_x, offset_y

    def _screen(self, point: tuple[float, float]) -> QPointF:
        scale, ox, oy = self._transform()
        return QPointF(point[0] * scale + ox, point[1] * scale + oy)

    def paintEvent(self, event):
        if not self.puzzle or not self.topology:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors = self._theme_colors()
        scale, _, _ = self._transform()
        solution = set(self.practice_edges) if self.practice_mode else set()
        if not self.practice_mode and self.show_solution:
            solution.update(self.puzzle.analysis.solution_edges or self.puzzle.target_solution_edges or [])
        target = set(self.puzzle.target_solution_edges or []) if self.edit_target and not self.practice_mode else set()
        for edge in self.topology.edges.values():
            color, width = colors["grid"], 1.5
            if edge.id in target:
                color, width = colors["target"], 5
            if edge.id in solution:
                color, width = colors["solution"], 6
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap))
            if edge.circle_center is None:
                a = self.topology.vertices[edge.vertices[0]]
                b = self.topology.vertices[edge.vertices[1]]
                painter.drawLine(self._screen((a.x, a.y)), self._screen((b.x, b.y)))
            else:
                center = self._screen(edge.circle_center)
                radius = (edge.circle_radius or 0.5) * scale
                rect = QRectF(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius)
                painter.drawArc(rect, int(-(edge.start_angle or 0) * 16), int(-(edge.span_angle or 60) * 16))
        clues = self.puzzle.clue_map()
        font = painter.font()
        font.setPointSizeF(max(9, min(20, scale * 0.19)))
        font.setBold(True)
        painter.setFont(font)
        for cell_id, clue in clues.items():
            point = self._screen(self.topology.cells[cell_id].center)
            painter.setPen(colors["clue"])
            text = "π" if clue.kind == ClueKind.PI else str(clue.value)
            painter.drawText(QRectF(point.x() - 20, point.y() - 16, 40, 32), Qt.AlignCenter, text)
            if clue.locked:
                painter.setPen(colors["lock"])
                painter.drawText(QRectF(point.x() + 9, point.y() - 18, 14, 14), Qt.AlignCenter, "•")
        if self.selected_cell and self.selected_cell in self.topology.cells:
            point = self._screen(self.topology.cells[self.selected_cell].center)
            painter.setPen(QPen(colors["selection"], 2, Qt.DashLine))
            painter.drawEllipse(point, 18, 18)

    def _edge_distance(self, position: QPointF, edge_id: str) -> float:
        edge = self.topology.edges[edge_id]
        if edge.circle_center is None:
            points = [self._screen((self.topology.vertices[v].x, self.topology.vertices[v].y)) for v in edge.vertices]
        else:
            cx, cy = edge.circle_center
            radius = edge.circle_radius or 0.5
            points = [
                self._screen((cx + radius * math.cos(math.radians((edge.start_angle or 0) + i * 10)), cy + radius * math.sin(math.radians((edge.start_angle or 0) + i * 10))))
                for i in range(7)
            ]
        best = float("inf")
        for a, b in zip(points, points[1:]):
            vx, vy = b.x() - a.x(), b.y() - a.y()
            wx, wy = position.x() - a.x(), position.y() - a.y()
            length2 = vx * vx + vy * vy
            t = max(0.0, min(1.0, (wx * vx + wy * vy) / length2)) if length2 else 0
            px, py = a.x() + t * vx, a.y() + t * vy
            best = min(best, math.hypot(position.x() - px, position.y() - py))
        return best

    def mousePressEvent(self, event):
        if event.button() in (Qt.MiddleButton, Qt.RightButton):
            self._pan_anchor = event.position()
            return
        if not self.puzzle or not self.topology or event.button() != Qt.LeftButton:
            return
        if self.practice_mode:
            edge_id, distance = min(((edge_id, self._edge_distance(event.position(), edge_id)) for edge_id in self.topology.edges), key=lambda item: item[1])
            if distance <= 14:
                self.practice_edges.symmetric_difference_update({edge_id})
                self.practice_edited.emit()
                self.update()
            return
        if self.edit_target:
            edge_id, distance = min(((edge_id, self._edge_distance(event.position(), edge_id)) for edge_id in self.topology.edges), key=lambda item: item[1])
            if distance <= 14:
                edges = set(self.puzzle.target_solution_edges or [])
                edges.symmetric_difference_update({edge_id})
                self.puzzle.target_solution_edges = sorted(edges)
                self.puzzle.clear_analysis()
                self.puzzle_edited.emit()
                self.update()
                return
        cell_id, distance = min(((cell_id, math.dist((event.position().x(), event.position().y()), (self._screen(cell.center).x(), self._screen(cell.center).y()))) for cell_id, cell in self.topology.cells.items()), key=lambda item: item[1])
        if distance <= 28:
            self.selected_cell = cell_id
            self.cell_selected.emit(cell_id)
            self.update()

    def mouseMoveEvent(self, event):
        if self._pan_anchor is not None:
            delta = event.position() - self._pan_anchor
            self.pan += delta
            self._pan_anchor = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() in (Qt.MiddleButton, Qt.RightButton):
            self._pan_anchor = None

    def wheelEvent(self, event):
        self.zoom = max(0.5, min(3.0, self.zoom * (1.1 if event.angleDelta().y() > 0 else 1 / 1.1)))
        self.update()


class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(str, float)

    def __init__(self, operation: str, puzzle: Puzzle, seconds: float = 60.0, generation_settings: dict | None = None):
        super().__init__()
        self.operation = operation
        self.puzzle = copy.deepcopy(puzzle)
        self.seconds = seconds
        self.generation_settings = generation_settings or {}
        self.cancelled = False

    @Slot()
    def run(self):
        try:
            if self.operation == "solve":
                self.finished.emit((self.puzzle, solve_puzzle(self.puzzle, time_limit=self.seconds)))
            else:
                options = GenerationOptions(
                    time_limit=self.seconds,
                    **self.generation_settings,
                    cancel_check=lambda: self.cancelled,
                    progress=lambda message, value: self.progress.emit(message, value),
                )
                self.finished.emit((self.puzzle, generate_puzzle(self.puzzle, options)))
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("特色数回题目生产系统")
        self.resize(1100, 760)
        self.canvas = PuzzleCanvas()
        self.setCentralWidget(self.canvas)
        self.path: Path | None = None
        self.thread: QThread | None = None
        self.worker: Worker | None = None
        self.practice_started_at: float | None = None
        self.practice_elapsed_seconds = 0.0
        self.practice_completed = False
        self.practice_clock = QTimer(self)
        self.practice_clock.setInterval(250)
        self.practice_clock.timeout.connect(self.update_practice_timer)
        self.status_label = QLabel("就绪")
        self.practice_timer_label = QLabel("练习 00:00")
        self.practice_timer_label.setMinimumWidth(120)
        self.practice_timer_label.setAlignment(Qt.AlignCenter)
        self.practice_timer_label.hide()
        self.progress = QProgressBar()
        self.progress.setMinimumWidth(360)
        self.progress.setMaximumWidth(520)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.progress.setAlignment(Qt.AlignCenter)
        self.progress.hide()
        self.statusBar().addWidget(self.status_label, 1)
        self.statusBar().addPermanentWidget(self.practice_timer_label)
        self.statusBar().addPermanentWidget(self.progress)
        self._build_actions()
        self._set_puzzle(Puzzle(Variant.CLASSIC, {"rows": 5, "cols": 5}))

    @property
    def puzzle(self) -> Puzzle:
        assert self.canvas.puzzle
        return self.canvas.puzzle

    def _build_actions(self):
        file_menu = self.menuBar().addMenu("文件")
        puzzle_menu = self.menuBar().addMenu("题目")
        practice_menu = self.menuBar().addMenu("练习")
        toolbar = QToolBar("工具")
        self.addToolBar(toolbar)

        def action(text, slot, menu=file_menu, checkable=False):
            item = QAction(text, self)
            item.setCheckable(checkable)
            item.triggered.connect(slot)
            menu.addAction(item)
            toolbar.addAction(item)
            return item

        action("新建经典", self.new_classic)
        action("新建特色", self.new_circle)
        action("打开", self.open_file)
        action("保存", self.save_file)
        action("另存为", self.save_as)
        action("导出 SVG", self.export_current)
        action("导出 PDF", self.export_pdf)
        action("校验曲线", self.validate_target, puzzle_menu)
        action("求解", lambda: self.start_worker("solve", 60.0), puzzle_menu)
        action("生成", self.configure_generation, puzzle_menu)
        action("取消任务", self.cancel_worker, puzzle_menu)
        action("设置数字", self.set_number, puzzle_menu)
        action("设置 π", self.set_pi, puzzle_menu)
        action("清除提示", self.clear_clue, puzzle_menu)
        action("锁定/解锁", self.toggle_lock, puzzle_menu)
        self.edit_action = action("编辑目标曲线", self.toggle_edit, puzzle_menu, True)
        self.edit_action.setChecked(True)
        self.solution_action = action("显示答案", self.toggle_solution, puzzle_menu, True)
        self.practice_action = action("练习模式", self.toggle_practice, practice_menu, True)
        self.verify_practice_action = action("验证作答", self.verify_practice, practice_menu)
        self.reset_practice_action = action("重置练习", self.reset_practice, practice_menu)
        self.verify_practice_action.setEnabled(False)
        self.reset_practice_action.setEnabled(False)
        self.canvas.practice_edited.connect(self.on_practice_edited)

    def _set_puzzle(self, puzzle: Puzzle, path: Path | None = None):
        try:
            self.canvas.set_puzzle(puzzle)
            self.path = path
            tier = puzzle.metadata.get("curated_difficulty") or puzzle.metadata.get("difficulty_tier")
            self.status_label.setText(f"题目已载入 · {tier}" if tier else "题目已载入")
            if hasattr(self, "practice_action") and self.practice_action.isChecked():
                self.reset_practice()
        except Exception as exc:
            QMessageBox.critical(self, "题目无效", str(exc))

    def new_classic(self):
        rows, ok = QInputDialog.getInt(self, "经典数回", "行数", 5, 1, 30)
        if not ok:
            return
        cols, ok = QInputDialog.getInt(self, "经典数回", "列数", 5, 1, 30)
        if ok:
            self._set_puzzle(Puzzle(Variant.CLASSIC, {"rows": rows, "cols": cols}))

    def new_circle(self):
        text, ok = QInputDialog.getText(self, "特色数回", "每行圆数（逗号分隔，相邻差 1）", text="4,5,4,5")
        if not ok:
            return
        try:
            lengths = [int(item.strip()) for item in text.split(",") if item.strip()]
            self._set_puzzle(Puzzle(Variant.CIRCLE_PACK, {"row_lengths": lengths}))
        except Exception as exc:
            QMessageBox.critical(self, "输入无效", str(exc))

    def open_file(self):
        name, _ = QFileDialog.getOpenFileName(self, "打开题目", "", "数回题目 (*.json)")
        if name:
            try:
                self._set_puzzle(load_puzzle(name), Path(name))
            except Exception as exc:
                QMessageBox.critical(self, "打开失败", str(exc))

    def save_file(self):
        if not self.path:
            return self.save_as()
        try:
            save_puzzle(self.puzzle, self.path)
            self.status_label.setText(f"已保存：{self.path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))

    def save_as(self):
        name, _ = QFileDialog.getSaveFileName(self, "保存题目", "puzzle.json", "数回题目 (*.json)")
        if name:
            self.path = Path(name)
            self.save_file()

    def export_current(self):
        name, _ = QFileDialog.getSaveFileName(self, "导出 SVG", "puzzle.svg", "SVG (*.svg)")
        if name:
            solution = self.puzzle.analysis.solution_edges if self.canvas.show_solution else None
            export_svg(self.puzzle, name, solution_edges=solution, title=self.puzzle.metadata.get("title"))
            self.status_label.setText("SVG 已导出")

    def export_pdf(self):
        name, _ = QFileDialog.getSaveFileName(self, "导出 PDF", "puzzle.pdf", "PDF (*.pdf)")
        if name:
            export_single_pdf(self.puzzle, name, show_solution=self.canvas.show_solution)
            self.status_label.setText("PDF 已导出")

    def validate_target(self):
        valid, message = validate_target_solution(self.puzzle)
        QMessageBox.information(self, "曲线校验" if valid else "曲线无效", message)

    def _selected_cell(self) -> str | None:
        if not self.canvas.selected_cell:
            QMessageBox.information(self, "选择单元格", "请先关闭目标曲线编辑或点击一个单元格。")
        return self.canvas.selected_cell

    def _replace_clue(self, clue: Clue | None):
        if self.canvas.practice_mode:
            return
        cell_id = self._selected_cell()
        if not cell_id:
            return
        self.puzzle.clues = [item for item in self.puzzle.clues if item.cell_id != cell_id]
        if clue:
            self.puzzle.clues.append(clue)
        self.puzzle.clear_analysis()
        self.canvas.update()

    def set_number(self):
        if self.canvas.practice_mode:
            QMessageBox.information(self, "练习模式", "练习模式中不能修改题目提示。")
            return
        cell_id = self._selected_cell()
        if not cell_id:
            return
        maximum = len(self.canvas.topology.cells[cell_id].edge_ids)
        value, ok = QInputDialog.getInt(self, "数字提示", f"输入 0–{maximum}", 0, 0, maximum)
        if ok:
            self._replace_clue(Clue(cell_id, ClueKind.NUMBER, value))

    def set_pi(self):
        if self.canvas.practice_mode:
            QMessageBox.information(self, "练习模式", "练习模式中不能修改题目提示。")
            return
        cell_id = self._selected_cell()
        if not cell_id:
            return
        if self.puzzle.variant != Variant.CIRCLE_PACK:
            QMessageBox.warning(self, "不可用", "π 仅适用于特色数回。")
            return
        self._replace_clue(Clue(cell_id, ClueKind.PI))

    def clear_clue(self):
        if self.canvas.practice_mode:
            QMessageBox.information(self, "练习模式", "练习模式中不能修改题目提示。")
            return
        self._replace_clue(None)

    def toggle_lock(self):
        if self.canvas.practice_mode:
            QMessageBox.information(self, "练习模式", "练习模式中不能修改题目提示。")
            return
        cell_id = self._selected_cell()
        clue = self.puzzle.clue_map().get(cell_id) if cell_id else None
        if clue:
            clue.locked = not clue.locked
            self.puzzle.clear_analysis()
            self.canvas.update()

    def toggle_edit(self, checked):
        if self.canvas.practice_mode:
            self.edit_action.setChecked(False)
            return
        self.canvas.edit_target = checked
        self.canvas.update()

    def toggle_solution(self, checked):
        if self.canvas.practice_mode:
            self.solution_action.setChecked(False)
            return
        self.canvas.show_solution = checked
        self.canvas.update()

    @staticmethod
    def format_elapsed(seconds: float) -> str:
        total = max(0, int(seconds))
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"

    def toggle_practice(self, checked: bool):
        self.canvas.practice_mode = checked
        self.canvas.practice_edges.clear()
        self.practice_completed = False
        self.edit_action.setChecked(False)
        self.solution_action.setChecked(False)
        self.canvas.edit_target = False
        self.canvas.show_solution = False
        self.edit_action.setEnabled(not checked)
        self.solution_action.setEnabled(not checked)
        self.verify_practice_action.setEnabled(checked)
        self.reset_practice_action.setEnabled(checked)
        if checked:
            self.reset_practice()
            self.status_label.setText("练习模式：点击边添加或删除作答曲线")
        else:
            self.practice_clock.stop()
            self.practice_started_at = None
            self.practice_elapsed_seconds = 0.0
            self.practice_timer_label.hide()
            self.status_label.setText("已退出练习模式")
        self.canvas.update()

    def reset_practice(self):
        if not self.canvas.practice_mode:
            return
        self.canvas.practice_edges.clear()
        self.practice_completed = False
        self.practice_elapsed_seconds = 0.0
        self.practice_started_at = time.monotonic()
        self.practice_timer_label.show()
        self.practice_clock.start()
        self.update_practice_timer()
        self.status_label.setText("练习已重新开始")
        self.canvas.update()

    def current_practice_elapsed(self) -> float:
        if self.practice_started_at is None:
            return self.practice_elapsed_seconds
        return self.practice_elapsed_seconds + time.monotonic() - self.practice_started_at

    def update_practice_timer(self):
        elapsed = self.current_practice_elapsed()
        self.practice_timer_label.setText(f"练习 {self.format_elapsed(elapsed)}")

    def on_practice_edited(self):
        if self.practice_completed:
            self.practice_completed = False
            self.practice_started_at = time.monotonic()
            self.practice_clock.start()
        self.status_label.setText(f"练习中：已选择 {len(self.canvas.practice_edges)} 条边")

    def verify_practice(self):
        if not self.canvas.practice_mode:
            return
        valid, message = validate_solution_edges(self.puzzle, self.canvas.practice_edges, check_clues=True)
        if valid:
            elapsed = self.current_practice_elapsed()
            self.practice_elapsed_seconds = elapsed
            self.practice_started_at = None
            self.practice_completed = True
            self.practice_clock.stop()
            self.update_practice_timer()
            formatted = self.format_elapsed(elapsed)
            self.status_label.setText(f"作答正确，用时 {formatted}")
            QMessageBox.information(self, "练习完成", f"回答正确！\n用时：{formatted}")
        else:
            self.status_label.setText("作答尚未通过验证，计时继续")
            QMessageBox.warning(self, "尚未完成", f"当前作答不正确：\n{message}\n\n计时将继续。")

    def configure_generation(self):
        seconds, ok = QInputDialog.getInt(self, "生成设置", "最长计算时间（秒）", 300, 10, 1800, 10)
        if not ok:
            return
        pi_choices = ["自动选择并优先保留 π", "必须包含 π", "不使用 π"]
        pi_choice, ok = QInputDialog.getItem(self, "生成设置", "π 提示策略", pi_choices, 0, False)
        if not ok:
            return
        difficulty_choices = ["不限定", "初级 Beginner", "中级 Medium", "高级 Difficult", "专家 Expert"]
        difficulty_choice, ok = QInputDialog.getItem(self, "生成设置", "目标难度", difficulty_choices, 0, False)
        if not ok:
            return
        difficulty = {
            "初级 Beginner": "beginner",
            "中级 Medium": "medium",
            "高级 Difficult": "difficult",
            "专家 Expert": "expert",
        }.get(difficulty_choice)
        settings = {
            "auto_pi": pi_choice != "不使用 π",
            "require_pi": pi_choice == "必须包含 π",
            "prefer_pi": pi_choice != "不使用 π",
            "target_difficulty": difficulty,
            "max_pi_candidates": 24,
        }
        self.start_worker("generate", float(seconds), settings)

    def start_worker(self, operation: str, seconds: float, generation_settings: dict | None = None):
        if self.thread:
            return
        self.thread = QThread(self)
        self.worker = Worker(operation, self.puzzle, seconds, generation_settings)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.failed.connect(self.on_worker_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.on_thread_finished)
        self.progress.setValue(0)
        self.progress.show()
        self.status_label.setText("正在求解…" if operation == "solve" else "正在生成…")
        self.thread.start()

    def cancel_worker(self):
        if self.worker:
            self.worker.cancelled = True
            self.status_label.setText("正在安全取消…")

    @Slot(str, float)
    def on_progress(self, message: str, value: float):
        self.status_label.setText(message)
        self.progress.setValue(round(value * 100))

    @Slot(object)
    def on_worker_finished(self, payload):
        source, result = payload
        if hasattr(result, "puzzle"):
            if result.puzzle:
                self._set_puzzle(result.puzzle, self.path)
            self.status_label.setText(result.message)
        else:
            self._set_puzzle(source, self.path)
            self.status_label.setText(result.message)
        self.progress.hide()

    @Slot(str)
    def on_worker_failed(self, message: str):
        self.progress.hide()
        QMessageBox.critical(self, "操作失败", message)

    def on_thread_finished(self):
        if self.thread:
            self.thread.deleteLater()
        self.thread = None
        self.worker = None

    def closeEvent(self, event):
        if self.worker:
            self.worker.cancelled = True
            self.thread.quit()
            self.thread.wait(2000)
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("特色数回")
    app.setFont(QFont("Microsoft YaHei UI" if sys.platform == "win32" else "Noto Sans CJK SC", 10))
    window = MainWindow()
    window.show()
    if os.environ.get("SHUHUI_SMOKE_TEST") == "1":
        QTimer.singleShot(700, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
