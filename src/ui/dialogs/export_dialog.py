"""导出对话框"""

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QCheckBox, QPushButton,
    QFileDialog, QDialogButtonBox, QGroupBox, QLineEdit
)


class ExportDialog(QDialog):
    """导出对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出")
        self.setMinimumSize(400, 250)
        self._export_path = Path.home() / "power_tree_export"
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 导出路径
        path_group = QGroupBox("导出路径")
        path_layout = QHBoxLayout(path_group)
        self._path_edit = QLineEdit()
        self._path_edit.setText(str(self._export_path))
        self._path_edit.setReadOnly(True)
        path_layout.addWidget(self._path_edit)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(browse_btn)
        layout.addWidget(path_group)

        # 导出格式
        fmt_group = QGroupBox("导出选项")
        fmt_layout = QVBoxLayout(fmt_group)

        self._csv_check = QCheckBox("导出计算结果报表 (CSV)")
        self._csv_check.setChecked(True)
        fmt_layout.addWidget(self._csv_check)

        self._png_check = QCheckBox("导出树形图 (PNG)")
        self._png_check.setChecked(True)
        fmt_layout.addWidget(self._png_check)

        self._svg_check = QCheckBox("导出树形图 (SVG)")
        self._svg_check.setChecked(False)
        fmt_layout.addWidget(self._svg_check)

        layout.addWidget(fmt_group)

        # 按钮
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _browse_path(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "选择导出目录", str(self._export_path))
        if path:
            self._export_path = Path(path)
            self._path_edit.setText(str(self._export_path))

    @property
    def export_path(self) -> Path:
        return self._export_path

    @property
    def export_csv(self) -> bool:
        return self._csv_check.isChecked()

    @property
    def export_png(self) -> bool:
        return self._png_check.isChecked()

    @property
    def export_svg(self) -> bool:
        return self._svg_check.isChecked()
