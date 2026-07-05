"""电源树设计器 — 入口文件"""

import sys
import os
from pathlib import Path

# ── 确定项目根目录 ──────────────────────────────────
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后: 资源在 _MEIPASS 临时目录
    BASE_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

# 将项目根目录加入 sys.path，确保 src 模块可导入
sys.path.insert(0, str(BASE_DIR))
os.chdir(str(BASE_DIR))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PowerTreeDesigner")
    app.setOrganizationName("PowerTreeDesigner")

    # 全局字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    # 全局样式
    app.setStyleSheet("""
        QMainWindow {
            background-color: #F5F5F5;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #E0E0E0;
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 14px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QTreeWidget {
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            background-color: white;
        }
        QTreeWidget::item {
            padding: 3px 0;
        }
        QTreeWidget::item:hover {
            background-color: #E3F2FD;
        }
        QLineEdit, QDoubleSpinBox, QComboBox {
            border: 1px solid #BDBDBD;
            border-radius: 3px;
            padding: 2px 6px;
        }
        QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border-color: #1976D2;
        }
        QPushButton {
            background-color: #1976D2;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 5px 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1565C0;
        }
        QPushButton:pressed {
            background-color: #0D47A1;
        }
        QToolBar {
            background-color: #FAFAFA;
            border-bottom: 1px solid #E0E0E0;
            spacing: 4px;
            padding: 2px;
        }
        QToolBar QPushButton {
            background-color: transparent;
            color: #424242;
            border: 1px solid transparent;
            padding: 4px 10px;
            font-weight: normal;
        }
        QToolBar QPushButton:hover {
            background-color: #E3F2FD;
            border-color: #BBDEFB;
        }
        QStatusBar {
            background-color: #FAFAFA;
            border-top: 1px solid #E0E0E0;
        }
        QSplitter::handle {
            background-color: #E0E0E0;
            width: 2px;
        }
    """)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
