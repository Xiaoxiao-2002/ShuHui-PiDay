class ShuhuiError(Exception):
    """项目异常基类。"""


class PuzzleFormatError(ShuhuiError):
    """题目文件或字段不合规。"""


class TopologyError(ShuhuiError):
    """棋盘拓扑无法构造。"""


class GenerationError(ShuhuiError):
    """题目无法生成。"""

