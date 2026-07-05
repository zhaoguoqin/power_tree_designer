"""电源树数据结构 — 管理树节点的增删改查"""

from typing import Optional
from PySide6.QtCore import QObject, Signal

from src.models.tree_node import TreeNode
from src.models.power_module import PowerModule, ModuleType, get_type_display
from src.core.calculator import Calculator


class PowerTree(QObject):
    """电源树管理器"""

    tree_changed = Signal()               # 树结构变更
    node_changed = Signal(str)            # 节点参数变更 (node_id)
    node_selected = Signal(str)           # 节点被选中
    calculation_updated = Signal()        # 计算结果更新
    selection_cleared = Signal()          # 取消选中

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nodes: dict[str, TreeNode] = {}
        self._selected_node_id: Optional[str] = None
        self._modules: dict[str, PowerModule] = {}

    # ── 属性 ─────────────────────────────────────────

    @property
    def nodes(self) -> dict[str, TreeNode]:
        return self._nodes

    @property
    def root(self) -> Optional[TreeNode]:
        roots = [n for n in self._nodes.values() if n.is_root]
        return roots[0] if roots else None

    @property
    def selected_node(self) -> Optional[TreeNode]:
        if self._selected_node_id:
            return self._nodes.get(self._selected_node_id)
        return None

    @property
    def selected_node_id(self) -> Optional[str]:
        return self._selected_node_id

    # ── 模块引用 ──────────────────────────────────────

    def set_modules(self, modules: dict[str, PowerModule]) -> None:
        self._modules = modules

    def get_module(self, module_id: str) -> Optional[PowerModule]:
        return self._modules.get(module_id)

    # ── 节点操作 ──────────────────────────────────────

    def add_node(self, module: PowerModule,
                 parent_id: Optional[str] = None,
                 pos_x: float = 0, pos_y: float = 0) -> TreeNode:
        """添加节点到树中"""
        type_str = module.type.value if isinstance(module.type, ModuleType) else module.type
        type_disp = module.type_display or get_type_display(type_str)
        node = TreeNode(
            module_id=module.id,
            name=module.name,
            module_type=type_str,
            type_display=type_disp,
            chip_name=module.chip_name,
            output_voltage=module.output_voltage,
            output_current=module.max_output_current if module.type == ModuleType.LOAD else 0.0,
            parent_id=parent_id,
            pos_x=pos_x,
            pos_y=pos_y,
        )
        # 如果父节点存在，关联到父节点
        if parent_id and parent_id in self._nodes:
            parent = self._nodes[parent_id]
            parent.children_ids.append(node.id)
            node.input_voltage = parent.output_voltage

        self._nodes[node.id] = node
        self.tree_changed.emit()
        return node

    def remove_node(self, node_id: str) -> bool:
        """删除节点及其子树"""
        if node_id not in self._nodes:
            return False
        node = self._nodes[node_id]

        # 递归删除所有子节点
        for child_id in list(node.children_ids):
            self.remove_node(child_id)

        # 从父节点移除引用
        if node.parent_id and node.parent_id in self._nodes:
            parent = self._nodes[node.parent_id]
            if node_id in parent.children_ids:
                parent.children_ids.remove(node_id)

        if self._selected_node_id == node_id:
            self._selected_node_id = None
            self.selection_cleared.emit()

        del self._nodes[node_id]
        self.tree_changed.emit()
        return True

    def set_parent(self, node_id: str, new_parent_id: Optional[str]) -> bool:
        """更改节点的父节点"""
        if node_id not in self._nodes:
            return False
        node = self._nodes[node_id]

        # 防止循环引用
        if new_parent_id and new_parent_id in self._nodes:
            if self._is_descendant(new_parent_id, node_id):
                return False

        # 从旧父节点移除
        if node.parent_id and node.parent_id in self._nodes:
            old_parent = self._nodes[node.parent_id]
            if node_id in old_parent.children_ids:
                old_parent.children_ids.remove(node_id)

        # 设置新父节点
        node.parent_id = new_parent_id
        if new_parent_id and new_parent_id in self._nodes:
            new_parent = self._nodes[new_parent_id]
            if node_id not in new_parent.children_ids:
                new_parent.children_ids.append(node_id)

        self.tree_changed.emit()
        return True

    def update_node_params(self, node_id: str, **kwargs) -> bool:
        """更新节点参数"""
        if node_id not in self._nodes:
            return False
        node = self._nodes[node_id]
        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)
        self.node_changed.emit(node_id)
        return True

    def select_node(self, node_id: Optional[str]) -> None:
        """选中节点"""
        self._selected_node_id = node_id
        if node_id:
            self.node_selected.emit(node_id)
        else:
            self.selection_cleared.emit()

    def clear(self) -> None:
        """清空树"""
        self._nodes.clear()
        self._selected_node_id = None
        self.tree_changed.emit()
        self.selection_cleared.emit()

    # ── 计算 ──────────────────────────────────────────

    def recalculate(self) -> dict:
        """重新计算整棵树"""
        summary = Calculator.calculate_all(self._nodes, self._modules)
        self.calculation_updated.emit()
        return summary

    # ── 序列化 ────────────────────────────────────────

    def to_dict(self) -> dict:
        """序列化整棵树"""
        return {
            "nodes": {nid: node.to_dict() for nid, node in self._nodes.items()},
            "root_id": self.root.id if self.root else None,
        }

    def from_dict(self, data: dict) -> None:
        """从字典恢复树"""
        self.clear()
        nodes_data = data.get("nodes", {})
        for nid, ndata in nodes_data.items():
            node = TreeNode.from_dict(ndata)
            self._nodes[nid] = node
        self.tree_changed.emit()

    # ── 辅助 ──────────────────────────────────────────

    def _is_descendant(self, ancestor_id: str, node_id: str) -> bool:
        """检查 ancestor_id 是否是 node_id 的子孙"""
        node = self._nodes.get(node_id)
        if not node:
            return False
        for child_id in node.children_ids:
            if child_id == ancestor_id:
                return True
            if self._is_descendant(ancestor_id, child_id):
                return True
        return False

    def get_node_depth(self, node_id: str) -> int:
        """获取节点的深度（根深度为 0）"""
        depth = 0
        current = self._nodes.get(node_id)
        while current and current.parent_id:
            depth += 1
            current = self._nodes.get(current.parent_id)
        return depth

    def get_children_at_depth(self, node_id: str, depth: int) -> list[TreeNode]:
        """获取指定节点下指定深度的所有子孙"""
        if depth == 0:
            node = self._nodes.get(node_id)
            return [node] if node else []
        node = self._nodes.get(node_id)
        if not node:
            return []
        result = []
        for child_id in node.children_ids:
            result.extend(self.get_children_at_depth(child_id, depth - 1))
        return result
