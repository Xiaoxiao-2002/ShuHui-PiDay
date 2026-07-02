import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

from shuhui.gui import MainWindow
from shuhui.model import Clue, ClueKind, Puzzle, Variant
from shuhui.topology import build_topology


def test_main_window_smoke():
    app = QApplication.instance() or QApplication([])
    app.setFont(QFont("Microsoft YaHei UI", 10))
    window = MainWindow()
    assert window.puzzle.board == {"rows": 5, "cols": 5}
    assert window.canvas.topology is not None
    assert window.progress.minimumWidth() == 360
    assert window.progress.maximumWidth() == 520
    assert window.progress.format() == "%p%"
    dark_palette = window.canvas.palette()
    dark_palette.setColor(QPalette.Window, QColor("#202020"))
    dark_palette.setColor(QPalette.WindowText, QColor("#f5f5f5"))
    window.canvas.setPalette(dark_palette)
    colors = window.canvas._theme_colors()
    assert colors["clue"].lightness() > 200
    assert colors["solution"].lightness() > 120
    window.close()


def test_practice_mode_hides_answer_tracks_time_and_accepts_solution(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    puzzle = Puzzle(Variant.CLASSIC, {"rows": 1, "cols": 1}, [Clue("cell:0:0", ClueKind.NUMBER, 4)])
    topology = build_topology(puzzle)
    puzzle.target_solution_edges = list(topology.cells["cell:0:0"].edge_ids)
    window._set_puzzle(puzzle)
    window.practice_action.setChecked(True)
    window.toggle_practice(True)
    assert window.canvas.practice_mode
    assert not window.canvas.show_solution
    assert not window.canvas.edit_target
    assert window.canvas.practice_edges == set()
    assert window.practice_clock.isActive()
    window.canvas.practice_edges.update(puzzle.target_solution_edges)
    monkeypatch.setattr("shuhui.gui.QMessageBox.information", lambda *args, **kwargs: None)
    window.verify_practice()
    assert window.practice_completed
    assert not window.practice_clock.isActive()
    assert "作答正确" in window.status_label.text()
    window.toggle_practice(False)
    assert not window.canvas.practice_mode
    assert not window.practice_timer_label.isVisible()
    window.close()
