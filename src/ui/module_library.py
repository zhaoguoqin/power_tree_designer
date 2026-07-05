"""模块库面板 — 分类显示电源模块，支持拖放"""

from pathlib import Path
from PySide6.QtCore import Qt, Signal, QMimeData, QSize, QPoint
from PySide6.QtGui import QIcon, QAction, QDrag, QPixmap, QPainter, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QMenu, QPushButton, QHBoxLayout, QMessageBox,
    QLineEdit, QInputDialog, QAbstractItemView, QApplication
)

from src.models.power_module import PowerModule, ModuleType
from src.core.module_manager import ModuleManager


def _module_type_icon(mtype: ModuleType) -> str:
    icons = {
        ModuleType.INPUT_SOURCE: "⚡",
        ModuleType.BUCK: "⬇",
        ModuleType.BOOST: "⬆",
        ModuleType.BUCK_BOOST: "🔄",
        ModuleType.LDO: "▬",
        ModuleType.LOAD: "📱",
        ModuleType.OTHER: "❓",
    }
    return icons.get(mtype, "❓")


def _module_type_color(mtype: ModuleType) -> QColor:
    colors = {
        ModuleType.INPUT_SOURCE: QColor("#2196F3"),
        ModuleType.BUCK: QColor("#4CAF50"),
        ModuleType.BOOST: QColor("#FF9800"),
        ModuleType.BUCK_BOOST: QColor("#9C27B0"),
        ModuleType.LDO: QColor("#00BCD4"),
        ModuleType.LOAD: QColor("#F44336"),
        ModuleType.OTHER: QColor("#607D8B"),
    }
    return colors.get(mtype, QColor("#607D8B"))


class _DraggableTreeWidget(QTreeWidget):
    """支持自定义 MIME 数据拖放的 QTreeWidget

    使用 mouseMoveEvent 手动触发拖放，比重写 startDrag 更可靠。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_start_pos: QPoint = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return

        # 检查是否移动足够距离来触发拖放
        if (event.pos() - self._drag_start_pos).manhattanLength() \
                < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        # 获取当前项
        item = self.itemAt(self._drag_start_pos)
        if not item:
            super().mouseMoveEvent(event)
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data == "__category__":
            super().mouseMoveEvent(event)
            return

        # 创建拖放
        mime_data = QMimeData()
        mime_data.setData("application/x-power-module", data.encode())
        mime_data.setText(item.text(0))

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        # 拖放预览图
        pixmap = QPixmap(160, 34)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#E3F2FD"))
        painter.setPen(QPen(QColor("#1976D2"), 2))
        painter.drawRoundedRect(1, 1, 157, 31, 6, 6)
        font = QFont("Microsoft YaHei", 9)
        painter.setFont(font)
        painter.setPen(QColor("#1565C0"))
        label = item.text(0)
        if label and ord(label[0]) > 127:
            label = label[2:] if len(label) > 2 else label
        painter.drawText(8, 22, label)
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(80, 17))

        drag.exec(Qt.DropAction.CopyAction)


class ModuleLibrary(QWidget):
    """模块库面板"""

    module_selected = Signal(PowerModule)
    module_add_requested = Signal()
    module_edit_requested = Signal(str)
    module_delete_requested = Signal(str)
    module_duplicate_requested = Signal(str)

    def __init__(self, module_manager: ModuleManager, parent=None):
        super().__init__(parent)
        self._module_manager = module_manager
        self._search_text = ""

        self._setup_ui()
        self._connect_signals()
        self._populate()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 标题
        title = QLabel("模块库")
        title_font = QFont("Microsoft YaHei", 11)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # 搜索框
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索模块...")
        self._search_input.setClearButtonEnabled(True)
        layout.addWidget(self._search_input)

        # 树形列表 — 使用支持拖放子类
        self._tree = _DraggableTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(16)
        # 不启用 Qt 内置拖放，完全由自定义 mouseMoveEvent 处理
        self._tree.setDragEnabled(False)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.setIconSize(QSize(20, 20))
        layout.addWidget(self._tree, 1)

        # 按钮栏
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        self._new_btn = QPushButton("新建")
        self._new_btn.setToolTip("新建自定义电源模块")
        self._edit_btn = QPushButton("编辑")
        self._edit_btn.setToolTip("编辑选中模块")
        self._delete_btn = QPushButton("删除")
        self._delete_btn.setToolTip("删除选中模块")
        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.setToolTip("重新加载模块库")

        for btn in [self._new_btn, self._edit_btn, self._delete_btn,
                     self._refresh_btn]:
            btn.setMaximumHeight(28)
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

        # 提示
        hint = QLabel("拖拽模块到画布添加节点")
        hint.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(hint)

    def _connect_signals(self) -> None:
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)

        self._search_input.textChanged.connect(self._on_search)

        self._new_btn.clicked.connect(self.module_add_requested.emit)
        self._edit_btn.clicked.connect(self._edit_selected)
        self._delete_btn.clicked.connect(self._delete_selected)
        self._refresh_btn.clicked.connect(self._module_manager.refresh)

        self._module_manager.modules_changed.connect(self._populate)

    # ── 填充数据 ──────────────────────────────────────

    def _populate(self) -> None:
        """重新填充模块列表"""
        self._tree.clear()

        cats = self._module_manager.get_categories()
        for cat_name, modules in cats.items():
            cat_item = QTreeWidgetItem(self._tree)
            cat_item.setText(0, cat_name)
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
            cat_font = cat_item.font(0)
            cat_font.setBold(True)
            cat_item.setFont(0, cat_font)
            cat_item.setData(0, Qt.ItemDataRole.UserRole, "__category__")

            for mod in modules:
                if self._search_text and self._search_text.lower() not in mod.name.lower():
                    continue
                mod_item = QTreeWidgetItem(cat_item)
                icon_text = _module_type_icon(mod.type)
                mod_item.setText(0, f"{icon_text}  {mod.name}")
                mod_item.setToolTip(0, self._module_tooltip(mod))
                mod_item.setData(0, Qt.ItemDataRole.UserRole, mod.id)
                mod_item.setSizeHint(0, QSize(0, 28))
                color = _module_type_color(mod.type)
                mod_item.setForeground(0, color)

            if cat_item.childCount() == 0:
                self._tree.invisibleRootItem().removeChild(cat_item)

        self._tree.expandAll()

    def _module_tooltip(self, mod: PowerModule) -> str:
        lines = [
            f"Name: {mod.name}",
            f"Type: {ModuleType.display_name(mod.type)}",
            f"Desc: {mod.description}",
        ]
        if mod.type != ModuleType.INPUT_SOURCE:
            lines.append(f"Vin: {mod.input_voltage_min}~{mod.input_voltage_max}V")
            lines.append(f"Vout: {mod.output_voltage}V")
            lines.append(f"Imax: {mod.max_output_current}A")
            lines.append(f"Eff: {mod.efficiency * 100:.0f}%")
        return "\n".join(lines)

    # ── 搜索 ──────────────────────────────────────────

    def _on_search(self, text: str) -> None:
        self._search_text = text
        self._populate()

    # ── 交互 ──────────────────────────────────────────

    def _on_item_clicked(self, item: QTreeWidgetItem, col: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data != "__category__":
            mod = self._module_manager.get_module(data)
            if mod:
                self.module_selected.emit(mod)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, col: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data != "__category__":
            self.module_edit_requested.emit(data)

    def _edit_selected(self) -> None:
        item = self._tree.currentItem()
        if item:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data != "__category__":
                self.module_edit_requested.emit(data)

    def _delete_selected(self) -> None:
        item = self._tree.currentItem()
        if item:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data != "__category__":
                mod = self._module_manager.get_module(data)
                if mod:
                    reply = QMessageBox.question(
                        self, "Confirm Delete",
                        f"Delete module \"{mod.name}\"?\nThis cannot be undone.",
                        QMessageBox.StandardButton.Yes |
                        QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        self.module_delete_requested.emit(data)

    def _show_context_menu(self, pos: QPoint) -> None:
        item = self._tree.itemAt(pos)
        menu = QMenu(self)

        new_action = menu.addAction("New Module")
        new_action.triggered.connect(self.module_add_requested.emit)

        if item:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data != "__category__":
                edit_action = menu.addAction("Edit Module")
                edit_action.triggered.connect(
                    lambda d=data: self.module_edit_requested.emit(d))
                dup_action = menu.addAction("Duplicate Module")
                dup_action.triggered.connect(
                    lambda d=data: self.module_duplicate_requested.emit(d))
                menu.addSeparator()
                del_action = menu.addAction("Delete Module")
                del_action.triggered.connect(
                    lambda d=data: self.module_delete_requested.emit(d))

        menu.addSeparator()
        refresh_action = menu.addAction("Refresh")
        refresh_action.triggered.connect(self._module_manager.refresh)
        menu.exec(self._tree.mapToGlobal(pos))
