"""模块管理器 — 扫描、加载、保存电源模块 JSON 文件"""

import json
import shutil
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, Signal

from src.models.power_module import PowerModule, ModuleType


class ModuleManager(QObject):
    """管理电源模块库"""

    modules_changed = Signal()         # 模块库变更信号
    module_added = Signal(str)         # 模块名称
    module_removed = Signal(str)       # 模块名称

    def __init__(self, modules_dir: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self._modules_dir = Path(modules_dir) if modules_dir else Path("modules")
        self._modules_dir.mkdir(parents=True, exist_ok=True)
        self._modules: dict[str, PowerModule] = {}  # id -> PowerModule

    @property
    def modules_dir(self) -> Path:
        return self._modules_dir

    @property
    def modules(self) -> dict[str, PowerModule]:
        return self._modules

    def get_module(self, module_id: str) -> Optional[PowerModule]:
        return self._modules.get(module_id)

    def get_module_by_name(self, name: str) -> Optional[PowerModule]:
        for mod in self._modules.values():
            if mod.name == name:
                return mod
        return None

    def get_modules_by_type(self, module_type: ModuleType) -> list[PowerModule]:
        return [m for m in self._modules.values() if m.type == module_type]

    def get_modules_by_category(self, category: str) -> list[PowerModule]:
        return [m for m in self._modules.values() if m.category == category]

    def get_categories(self) -> dict[str, list[PowerModule]]:
        """获取所有分类及其模块"""
        cats: dict[str, list[PowerModule]] = {}
        for m in self._modules.values():
            cat = m.category or ModuleType.category_name(m.type)
            cats.setdefault(cat, []).append(m)
        return cats

    def load_all(self) -> int:
        """扫描 modules_dir 下的所有 JSON 文件并加载"""
        self._modules.clear()
        count = 0
        for fpath in self._modules_dir.glob("*.json"):
            try:
                mod = PowerModule.load_from_file(fpath)
                self._modules[mod.id] = mod
                count += 1
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"[WARN] 跳过无效模块文件 {fpath.name}: {e}")
        self.modules_changed.emit()
        return count

    def save_module(self, module: PowerModule) -> Path:
        """保存模块到文件，返回文件路径"""
        self._modules[module.id] = module
        fpath = self._modules_dir / f"{module.name}.json"
        module.save_to_file(fpath)
        self.module_added.emit(module.name)
        self.modules_changed.emit()
        return fpath

    def delete_module(self, module_id: str) -> bool:
        """删除模块（同时删除 JSON 文件）"""
        mod = self._modules.get(module_id)
        if mod is None:
            return False
        fpath = self._modules_dir / f"{mod.name}.json"
        if fpath.exists():
            fpath.unlink()
        name = mod.name
        del self._modules[module_id]
        self.module_removed.emit(name)
        self.modules_changed.emit()
        return True

    def duplicate_module(self, module_id: str, new_name: str) -> Optional[PowerModule]:
        """复制模块"""
        mod = self._modules.get(module_id)
        if mod is None:
            return None
        new_mod = PowerModule.from_dict(mod.to_dict())
        new_mod.name = new_name
        self.save_module(new_mod)
        return new_mod

    def refresh(self) -> int:
        """重新扫描文件夹"""
        return self.load_all()

    def export_module(self, module_id: str, dest_dir: Path) -> bool:
        """导出模块到指定目录"""
        mod = self._modules.get(module_id)
        if mod is None:
            return False
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        mod.save_to_file(dest_dir / f"{mod.name}.json")
        return True

    def import_module(self, filepath: Path) -> Optional[PowerModule]:
        """从文件导入模块"""
        try:
            mod = PowerModule.load_from_file(filepath)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"[WARN] 无法导入模块文件 {filepath}: {e}")
            return None
        self.save_module(mod)
        return mod
