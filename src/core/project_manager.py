"""项目管理器 — 保存/加载电源树项目"""

import json
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, Signal, QSettings

from src.core.power_tree import PowerTree


class ProjectManager(QObject):
    """项目文件管理"""

    project_saved = Signal(str)          # 文件路径
    project_loaded = Signal(str)         # 文件路径
    project_modified = Signal(bool)      # 是否有未保存的修改
    recent_files_changed = Signal()      # 最近文件列表变更

    MAX_RECENT_FILES = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_file: Optional[Path] = None
        self._modified: bool = False
        self._tree: Optional[PowerTree] = None
        self._settings = QSettings("PowerTreeDesigner", "PowerTreeDesigner")

    def set_tree(self, tree: PowerTree) -> None:
        """绑定电源树"""
        if self._tree:
            self._tree.tree_changed.disconnect(self._mark_modified)
            self._tree.node_changed.disconnect(self._mark_modified)
        self._tree = tree
        self._tree.tree_changed.connect(self._mark_modified)
        self._tree.node_changed.connect(self._mark_modified)

    @property
    def current_file(self) -> Optional[Path]:
        return self._current_file

    @property
    def is_modified(self) -> bool:
        return self._modified

    @property
    def project_name(self) -> str:
        if self._current_file:
            return self._current_file.stem
        return "未命名项目"

    def new_project(self) -> None:
        """新建项目"""
        if self._tree:
            self._tree.clear()
        self._current_file = None
        self._set_modified(False)

    def save(self) -> bool:
        """保存项目"""
        if self._current_file:
            return self._save_to_file(self._current_file)
        return False

    def save_as(self, filepath: Path) -> bool:
        """另存为"""
        path = Path(filepath)
        if path.suffix != ".pwt":
            path = path.with_suffix(".pwt")
        return self._save_to_file(path)

    def open(self, filepath: Path) -> bool:
        """打开项目"""
        path = Path(filepath)
        if not path.exists():
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if self._tree:
                self._tree.from_dict(data)
            self._current_file = path
            self._set_modified(False)
            self._add_recent_file(path)
            self.project_loaded.emit(str(path))
            return True
        except (json.JSONDecodeError, KeyError, OSError) as e:
            print(f"[ERROR] 无法打开项目文件 {path}: {e}")
            return False

    def get_recent_files(self) -> list[Path]:
        """获取最近打开的文件列表"""
        files_str = self._settings.value("recentFiles", [])
        if isinstance(files_str, str):
            files_str = json.loads(files_str) if files_str else []
        return [Path(f) for f in files_str if Path(f).exists()]

    def clear_recent_files(self) -> None:
        self._settings.setValue("recentFiles", [])
        self.recent_files_changed.emit()

    # ── 内部方法 ──────────────────────────────────────

    def _save_to_file(self, filepath: Path) -> bool:
        if self._tree is None:
            return False
        try:
            data = self._tree.to_dict()
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._current_file = filepath
            self._set_modified(False)
            self._add_recent_file(filepath)
            self.project_saved.emit(str(filepath))
            return True
        except OSError as e:
            print(f"[ERROR] 无法保存项目文件 {filepath}: {e}")
            return False

    def _set_modified(self, modified: bool) -> None:
        self._modified = modified
        self.project_modified.emit(modified)

    def _mark_modified(self, *args) -> None:
        """标记为已修改"""
        if not self._modified:
            self._set_modified(True)

    def _add_recent_file(self, filepath: Path) -> None:
        files = self.get_recent_files()
        fpath_str = str(filepath.resolve())
        # 去重并移到最前
        files = [f for f in files if str(f.resolve()) != fpath_str]
        files.insert(0, filepath)
        files = files[:self.MAX_RECENT_FILES]
        self._settings.setValue("recentFiles",
                                 [str(f.resolve()) for f in files])
        self.recent_files_changed.emit()
