"""电源树画布 — QGraphicsView 实现缩放、平移、网格背景"""

from typing import Optional
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QPainter, QPen, QColor, QBrush, QWheelEvent, QMouseEvent,
    QKeyEvent, QDragEnterEvent, QDragMoveEvent, QDropEvent,
    QPainterPath
)
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem, QMenu, QGraphicsTextItem
)

from src.models.tree_node import TreeNode
from src.models.power_module import PowerModule
from src.ui.tree_node_item import TreeNodeItem
from src.ui.tree_edge_item import TreeEdgeItem


class TreeCanvas(QGraphicsView):
    """电源树画布"""

    node_added = Signal(str, str, float, float)         # module_id, parent_id, x, y
    node_deleted = Signal(str)                           # node_id
    node_reparented = Signal(str, str)                   # node_id, new_parent_id
    node_selected = Signal(str)                          # node_id
    selection_cleared = Signal()
    module_dropped = Signal(str, float, float)           # module_id, x, y
    edge_dropped = Signal(str, str)                      # child_id, parent_id
    edge_clicked = Signal(str, str)                      # parent_id, child_id — 点击连线删除

    GRID_SIZE = 40
    MIN_ZOOM = 0.1
    MAX_ZOOM = 3.0

    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.setScene(self._scene)

        self._node_items: dict[str, TreeNodeItem] = {}   # node_id -> TreeNodeItem
        self._edge_items: dict[tuple, TreeEdgeItem] = {}  # (parent_id, child_id) -> edge
        self._zoom_level: float = 1.0
        self._panning: bool = False
        self._pan_start: QPointF = QPointF()
        self._edge_drag_source: Optional[TreeNodeItem] = None
        self._temp_edge: Optional[QGraphicsPathItem] = None
        self._edge_mode: bool = False

        # 视图设置
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setBackgroundBrush(QColor("#F5F5F5"))

        # 居中
        self.centerOn(0, 0)

        # 场景选中变化 → 通知外部
        self._scene.selectionChanged.connect(self._on_scene_selection_changed)

        # 右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    # ── 节点管理 ──────────────────────────────────────

    def add_node_item(self, node: TreeNode) -> TreeNodeItem:
        """添加节点图形项到画布"""
        item = TreeNodeItem(node)
        item.node_moved.connect(self._on_node_moved)
        item.node_double_clicked.connect(self._on_node_double_clicked)
        self._scene.addItem(item)
        self._node_items[node.id] = item
        return item

    def remove_node_item(self, node_id: str) -> None:
        """移除节点图形项"""
        item = self._node_items.pop(node_id, None)
        if item:
            self._scene.removeItem(item)
        # 移除相关连线
        edges_to_remove = [k for k in self._edge_items
                           if k[0] == node_id or k[1] == node_id]
        for key in edges_to_remove:
            edge = self._edge_items.pop(key, None)
            if edge:
                self._scene.removeItem(edge)

    def get_node_item(self, node_id: str) -> Optional[TreeNodeItem]:
        return self._node_items.get(node_id)

    def clear_all(self) -> None:
        """清除所有图形项"""
        for item in list(self._node_items.values()):
            self._scene.removeItem(item)
        for edge in list(self._edge_items.values()):
            self._scene.removeItem(edge)
        self._node_items.clear()
        self._edge_items.clear()

    # ── 连线管理 ──────────────────────────────────────

    def add_edge_item(self, parent_id: str, child_id: str,
                      power: float = 0.0, current: float = 0.0) -> Optional[TreeEdgeItem]:
        """添加连线"""
        parent_item = self._node_items.get(parent_id)
        child_item = self._node_items.get(child_id)
        if not parent_item or not child_item:
            return None
        edge = TreeEdgeItem(parent_id=parent_id, child_id=child_id)
        edge.set_flows(power, current)
        edge.edge_clicked.connect(
            lambda ids: self.edge_clicked.emit(ids[0], ids[1]))
        self._scene.addItem(edge)
        self._edge_items[(parent_id, child_id)] = edge
        self._update_edge_position(edge, parent_item, child_item)
        return edge

    def update_all_edges(self, node_map: dict[str, TreeNode]) -> None:
        """更新所有连线位置和标签"""
        for (pid, cid), edge in self._edge_items.items():
            p_item = self._node_items.get(pid)
            c_item = self._node_items.get(cid)
            if p_item and c_item:
                self._update_edge_position(edge, p_item, c_item)
            # 更新功率标签
            child = node_map.get(cid)
            if child:
                edge.set_flows(child.input_power, child.input_current)

    def sync_edges(self, node_map: dict[str, TreeNode]) -> None:
        """根据树结构同步连线（删除多余、创建缺失）"""
        existing = set(self._edge_items.keys())
        needed = set()
        for node in node_map.values():
            if node.parent_id:
                needed.add((node.parent_id, node.id))

        # 删除多余的
        for key in existing - needed:
            edge = self._edge_items.pop(key)
            self._scene.removeItem(edge)

        # 创建缺失的
        for key in needed - existing:
            self.add_edge_item(key[0], key[1])

        # 更新所有连线的位置
        self.update_all_edges(node_map)

    def _update_edge_position(self, edge: TreeEdgeItem,
                              parent: TreeNodeItem, child: TreeNodeItem) -> None:
        """更新连线端点位置"""
        source = parent.scene_output_point()
        target = child.scene_input_point()
        edge.set_points(source, target)

    # ── 自动布局 (改进层次树布局) ─────────────────────

    def auto_layout(self, node_map: dict[str, TreeNode],
                    root_id: Optional[str] = None) -> None:
        """使用改进的层次树布局算法"""
        if not node_map:
            return
        if root_id is None:
            roots = [n for n in node_map.values() if n.is_root]
            if not roots:
                return
            root_id = roots[0].id

        # 节点实际尺寸
        V_GAP = 160          # 层间距
        H_GAP = 80           # 最小水平间距

        def node_width(nid: str) -> float:
            it = self._node_items.get(nid)
            return it._calc_width() if it and hasattr(it, '_calc_width') else 220

        # ── 第一步：收集层次信息 ──
        levels: dict[str, int] = {}          # node_id → depth
        level_nodes: dict[int, list[str]] = {}  # depth → [node_ids]

        def assign_depth(nid: str, depth: int):
            levels[nid] = depth
            level_nodes.setdefault(depth, []).append(nid)
            for cid in node_map[nid].children_ids:
                assign_depth(cid, depth + 1)

        assign_depth(root_id, 0)
        max_depth = max(levels.values()) if levels else 0

        # ── 第二步：自底向上计算初步位置 ──
        x_pos: dict[str, float] = {}
        subtree_left: dict[str, float] = {}   # 子树左边界
        subtree_right: dict[str, float] = {}  # 子树右边界

        for depth in range(max_depth, -1, -1):
            for nid in level_nodes.get(depth, []):
                children = node_map[nid].children_ids
                if not children:
                    # 叶子节点：单独放置，稍后在同层对齐时调整
                    x_pos[nid] = 0  # 临时值
                    hw = node_width(nid) / 2
                    subtree_left[nid] = -hw
                    subtree_right[nid] = hw
                else:
                    # 内部节点：居中于子节点之上
                    child_xs = [x_pos[cid] for cid in children]
                    x_pos[nid] = (min(child_xs) + max(child_xs)) / 2
                    hw = node_width(nid) / 2
                    subtree_left[nid] = min(subtree_left[cid] for cid in children)
                    subtree_right[nid] = max(subtree_right[cid] for cid in children)
                    subtree_left[nid] = min(subtree_left[nid], x_pos[nid] - hw)
                    subtree_right[nid] = max(subtree_right[nid], x_pos[nid] + hw)

        # ── 第三步：逐层处理兄弟间距 ──
        for depth in range(1, max_depth + 1):
            nodes_at_depth = level_nodes.get(depth, [])
            # 按父节点分组
            parent_groups: dict[str, list[str]] = {}
            for nid in nodes_at_depth:
                pid = node_map[nid].parent_id
                if pid:
                    parent_groups.setdefault(pid, []).append(nid)

            for pid, siblings in parent_groups.items():
                if len(siblings) <= 1:
                    continue
                # 按 x 排序
                siblings.sort(key=lambda n: x_pos[n])
                # 从左到右检查并推开重叠
                for i in range(len(siblings) - 1):
                    a, b = siblings[i], siblings[i + 1]
                    min_gap = (node_width(a) + node_width(b)) / 2 + H_GAP
                    overlap = (x_pos[a] + node_width(a) / 2 + H_GAP) - x_pos[b]
                    if overlap > 0:
                        # 需要将 b 及其子树向右移动
                        shift = overlap
                        # 将 b 及后续兄弟整体右移
                        for j in range(i + 1, len(siblings)):
                            sj = siblings[j]
                            TreeCanvas._shift_subtree(sj, shift, node_map, x_pos,
                                          subtree_left, subtree_right)

            # 同层全部节点按 x 排序后，最后检查一次跨父节点的重叠
            if len(nodes_at_depth) > 1:
                nodes_at_depth.sort(key=lambda n: x_pos[n])
                for i in range(len(nodes_at_depth) - 1):
                    a, b = nodes_at_depth[i], nodes_at_depth[i + 1]
                    # 检查右键和左键是否重叠
                    gap = x_pos[b] - x_pos[a]
                    needed = (node_width(a) + node_width(b)) / 2 + H_GAP
                    if gap < needed:
                        # 将 b 子树整体右移
                        shift = needed - gap
                        TreeCanvas._shift_subtree(b, shift, node_map, x_pos,
                                      subtree_left, subtree_right)

        # ── 第四步：计算实际坐标并设置位置 ──
        for depth in range(max_depth + 1):
            nodes_at_depth = level_nodes.get(depth, [])
            y = depth * V_GAP
            for nid in nodes_at_depth:
                item = self._node_items.get(nid)
                if item:
                    nx = x_pos.get(nid, 0)
                    item.setPos(nx, y)
                    node_map[nid].pos_x = nx
                    node_map[nid].pos_y = y

        # 居中根节点在原点
        if root_id and root_id in x_pos:
            root_x = -x_pos[root_id]
            for nid, item in self._node_items.items():
                item.setPos(item.pos().x() + root_x, item.pos().y())
                node_map[nid].pos_x = item.pos().x()
                node_map[nid].pos_y = item.pos().y()

        # 第五步：处理未连接的孤立节点
        orphans = [n for n in node_map.values()
                   if n.is_root and n.id != root_id]
        ox = max((p.pos_x + node_width(p.id) / 2 + 60
                   for p in node_map.values()), default=0)
        for orphan in orphans:
            item = self._node_items.get(orphan.id)
            if item:
                item.setPos(ox, orphan.pos_y if orphan.pos_y else 0)
                node_map[orphan.id].pos_x = ox
                ox += node_width(orphan.id) + 80


    @staticmethod
    def _shift_subtree(node_id: str, shift: float,
                       node_map: dict,
                       x_pos: dict[str, float],
                       subtree_left: dict[str, float],
                       subtree_right: dict[str, float]):
        """将节点及其整个子树向右移动"""
        x_pos[node_id] += shift
        subtree_left[node_id] += shift
        subtree_right[node_id] += shift
        for cid in node_map[node_id].children_ids:
            TreeCanvas._shift_subtree(cid, shift, node_map, x_pos, subtree_left, subtree_right)

    # ── 事件处理 ──────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent):
        """滚轮缩放"""
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1 / 1.15
        new_zoom = self._zoom_level * factor
        if self.MIN_ZOOM <= new_zoom <= self.MAX_ZOOM:
            self._zoom_level = new_zoom
            self.scale(factor, factor)

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下"""
        # 中键平移
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        # 左键点击空白区域取消选中
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if item is None:
                self._scene.clearSelection()
                self.node_selected.emit("")
                self.selection_cleared.emit()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动"""
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放"""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        """键盘事件"""
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            selected = self._scene.selectedItems()
            for item in selected:
                if isinstance(item, TreeNodeItem):
                    self.node_deleted.emit(item.node_id)
        elif event.key() == Qt.Key.Key_F:
            self.fit_to_content()
        elif event.key() == Qt.Key.Key_0:
            self.reset_zoom()
        else:
            super().keyPressEvent(event)

    # ── 拖放支持 ──────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-power-module"):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasFormat("application/x-power-module"):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasFormat("application/x-power-module"):
            data = event.mimeData().data("application/x-power-module")
            module_id = bytes(data).decode()
            scene_pos = self.mapToScene(event.position().toPoint())
            self.module_dropped.emit(module_id, scene_pos.x(), scene_pos.y())
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            super().dropEvent(event)

    # ── 辅助 ──────────────────────────────────────────

    def drawBackground(self, painter: QPainter, rect: QRectF):
        """绘制网格背景"""
        painter.fillRect(rect, QColor("#FAFAFA"))

        # 浅色网格
        painter.setPen(QPen(QColor("#E0E0E0"), 0.5))
        left = int(rect.left()) - (int(rect.left()) % self.GRID_SIZE)
        top = int(rect.top()) - (int(rect.top()) % self.GRID_SIZE)

        lines = []
        for x in range(int(left), int(rect.right()), self.GRID_SIZE):
            lines.append(QPainterPath())
            lines[-1].moveTo(x, rect.top())
            lines[-1].lineTo(x, rect.bottom())
        for y in range(int(top), int(rect.bottom()), self.GRID_SIZE):
            lines.append(QPainterPath())
            lines[-1].moveTo(rect.left(), y)
            lines[-1].lineTo(rect.right(), y)
        for line in lines:
            painter.drawPath(line)

        # 原点十字
        painter.setPen(QPen(QColor("#BDBDBD"), 1.5))
        painter.drawLine(QPointF(0, rect.top()), QPointF(0, rect.bottom()))
        painter.drawLine(QPointF(rect.left(), 0), QPointF(rect.right(), 0))

    def fit_to_content(self) -> None:
        """缩放以适应所有内容"""
        if self._node_items:
            rect = QRectF()
            for item in self._node_items.values():
                rect = rect.united(item.sceneBoundingRect())
            rect.adjust(-50, -50, 50, 50)
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            self._zoom_level = self.transform().m11()

    def reset_zoom(self) -> None:
        """重置缩放"""
        self.resetTransform()
        self._zoom_level = 1.0

    def _show_context_menu(self, pos):
        """右键菜单"""
        menu = QMenu(self)
        fit_action = menu.addAction("适应窗口 (F)")
        fit_action.triggered.connect(self.fit_to_content)
        reset_action = menu.addAction("重置缩放 (0)")
        reset_action.triggered.connect(self.reset_zoom)
        menu.addSeparator()
        auto_action = menu.addAction("自动布局")
        auto_action.triggered.connect(lambda: self.auto_layout(
            {nid: item.node for nid, item in self._node_items.items()}))
        menu.exec(self.mapToGlobal(pos))

    def _on_scene_selection_changed(self) -> None:
        """场景选中变化时发出信号"""
        selected = self._scene.selectedItems()
        if selected:
            for item in selected:
                if isinstance(item, TreeNodeItem):
                    self.node_selected.emit(item.node_id)
                    return
        self.selection_cleared.emit()

    def _on_node_moved(self, node_id: str, x: float, y: float) -> None:
        """节点移动后更新连线"""
        item = self._node_items.get(node_id)
        if item:
            for (pid, cid), edge in self._edge_items.items():
                p_item = self._node_items.get(pid)
                c_item = self._node_items.get(cid)
                if p_item and c_item:
                    self._update_edge_position(edge, p_item, c_item)

    def _on_node_double_clicked(self, node_id: str) -> None:
        self.node_selected.emit(node_id)
