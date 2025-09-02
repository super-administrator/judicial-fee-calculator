"""
main.py
程序入口：抑制Qt冗余日志（macOS）、启动主窗体
"""

import os
import sys

# 抑制 Qt 冗余日志（需在导入/创建 QApplication 前设置）
os.environ["QT_LOGGING_RULES"] = "*.debug=false;*.info=false"

from PySide6.QtWidgets import QApplication
from ui import FeeCalculator


def main():
    app = QApplication(sys.argv)
    win = FeeCalculator()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
