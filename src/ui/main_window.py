"""主窗口 — 整合所有面板"""

import csv
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QStandardPaths
from PySide6.QtGui import QAction, QKeySequence, QFont, QPainter
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QStatusBar, QMenuBar, QMenu,
    QFileDialog, QMessageBox, QLabel, QVBoxLayout, QWidget,
    QToolBar, QApplication
)

from src.core.module_manager import ModuleManager
from src.core.power_tree import PowerTree
from src.core.project_manager import ProjectManager
from src.models.power_module import PowerModule, ModuleType
from src.models.tree_node import TreeNode
from src.ui.tree_canvas import TreeCanvas
from src.ui.module_library import ModuleLibrary
from src.ui.property_panel import PropertyPanel
from src.ui.dialogs.module_editor import ModuleEditorDialog
from src.ui.dialogs.export_dialog import ExportDialog


class MainWindow(QMainWindow):
    """电源树设计器主窗口"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("电源树设计器 - Power Tree Designer")
        self.setMinimumSize(1200, 750)
        self.resize(1400, 850)

        # ── 核心组件 ──
        self._module_manager = ModuleManager(Path("modules"))
        self._power_tree = PowerTree()
        self._project_manager = ProjectManager()

        # ── 初始化 ──
        self._module_manager.load_all()
        self._power_tree.set_modules(self._module_manager.modules)
        self._project_manager.set_tree(self._power_tree)

        # ── 设置 UI ──
        self._setup_central()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()

        # ── 更新状态 ──
        self._update_title()
        self._update_status()

    # ═══════════════════════════════════════════════════
    #  UI 构建
    # ═══════════════════════════════════════════════════

    def _setup_menu(self) -> None:
        """设置菜单栏"""
        mb = self.menuBar()

        # ── 文件菜单 ──
        file_menu = mb.addMenu("文件(&F)")

        new_act = QAction("新建项目(&N)", self)
        new_act.setShortcut(QKeySequence.StandardKey.New)
        new_act.triggered.connect(self._on_new_project)
        file_menu.addAction(new_act)

        open_act = QAction("打开项目(&O)...", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self._on_open_project)
        file_menu.addAction(open_act)

        file_menu.addSeparator()

        save_act = QAction("保存(&S)", self)
        save_act.setShortcut(QKeySequence.StandardKey.Save)
        save_act.triggered.connect(self._on_save_project)
        file_menu.addAction(save_act)

        save_as_act = QAction("另存为(&A)...", self)
        save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_act.triggered.connect(self._on_save_as_project)
        file_menu.addAction(save_as_act)

        file_menu.addSeparator()

        # 最近文件
        self._recent_menu = QMenu("最近打开(&R)", self)
        file_menu.addMenu(self._recent_menu)
        self._update_recent_menu()

        file_menu.addSeparator()

        export_act = QAction("导出(&E)...", self)
        export_act.setShortcut(QKeySequence("Ctrl+E"))
        export_act.triggered.connect(self._on_export)
        file_menu.addAction(export_act)

        file_menu.addSeparator()

        exit_act = QAction("退出(&X)", self)
        exit_act.setShortcut(QKeySequence("Alt+F4"))
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # ── 编辑菜单 ──
        edit_menu = mb.addMenu("编辑(&E)")

        add_root_act = QAction("添加根节点（输入电源）", self)
        add_root_act.triggered.connect(self._on_add_root_source)
        edit_menu.addAction(add_root_act)

        edit_menu.addSeparator()

        auto_layout_act = QAction("自动布局(&L)", self)
        auto_layout_act.setShortcut(QKeySequence("Ctrl+L"))
        auto_layout_act.triggered.connect(self._on_auto_layout)
        edit_menu.addAction(auto_layout_act)

        fit_act = QAction("适应窗口(&F)", self)
        fit_act.setShortcut(QKeySequence("Ctrl+F"))
        fit_act.triggered.connect(self._canvas.fit_to_content)
        edit_menu.addAction(fit_act)

        reset_zoom_act = QAction("重置缩放(&0)", self)
        reset_zoom_act.setShortcut(QKeySequence("Ctrl+0"))
        reset_zoom_act.triggered.connect(self._canvas.reset_zoom)
        edit_menu.addAction(reset_zoom_act)

        # ── 模块菜单 ──
        module_menu = mb.addMenu("模块(&M)")

        new_mod_act = QAction("新建模块...", self)
        new_mod_act.triggered.connect(self._on_new_module)
        module_menu.addAction(new_mod_act)

        import_mod_act = QAction("导入模块...", self)
        import_mod_act.triggered.connect(self._on_import_module)
        module_menu.addAction(import_mod_act)

        module_menu.addSeparator()

        export_mod_act = QAction("导出选中模块...", self)
        export_mod_act.triggered.connect(self._on_export_module)
        module_menu.addAction(export_mod_act)

        module_menu.addSeparator()

        refresh_act = QAction("刷新模块库", self)
        refresh_act.triggered.connect(self._module_manager.refresh)
        module_menu.addAction(refresh_act)

        # ── 帮助菜单 ──
        help_menu = mb.addMenu("帮助(&H)")

        about_act = QAction("关于(&A)", self)
        about_act.triggered.connect(self._on_about)
        help_menu.addAction(about_act)

    def _setup_toolbar(self) -> None:
        """设置工具栏"""
        tb = QToolBar("主工具栏", self)
        tb.setMovable(False)
        tb.setIconSize(tb.iconSize() * 0.8)

        tb.addAction("新建").triggered.connect(self._on_new_project)
        tb.addAction("打开").triggered.connect(self._on_open_project)
        tb.addAction("保存").triggered.connect(self._on_save_project)
        tb.addSeparator()
        tb.addAction("自动布局").triggered.connect(self._on_auto_layout)
        tb.addAction("适应").triggered.connect(self._canvas.fit_to_content)
        tb.addSeparator()
        tb.addAction("导出").triggered.connect(self._on_export)

        self.addToolBar(tb)

    def _setup_central(self) -> None:
        """设置中央区域：三栏布局"""
        central = QWidget()
        self.setCentralWidget(central)

        # 左侧：模块库
        self._module_library = ModuleLibrary(self._module_manager)

        # 中央：画布
        self._canvas = TreeCanvas()

        # 右侧：属性面板
        self._property_panel = PropertyPanel()

        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._module_library)
        splitter.addWidget(self._canvas)
        splitter.addWidget(self._property_panel)
        splitter.setStretchFactor(0, 1)   # 模块库
        splitter.setStretchFactor(1, 4)   # 画布
        splitter.setStretchFactor(2, 1)   # 属性面板
        splitter.setSizes([220, 700, 260])

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

    def _setup_statusbar(self) -> None:
        """设置状态栏"""
        self._status_label = QLabel("就绪")
        self.statusBar().addWidget(self._status_label, 1)
        self._summary_label = QLabel("")
        self.statusBar().addPermanentWidget(self._summary_label)

    # ═══════════════════════════════════════════════════
    #  信号连接
    # ═══════════════════════════════════════════════════

    def _connect_signals(self) -> None:
        """连接所有信号"""

        # 画布信号
        self._canvas.module_dropped.connect(self._on_module_dropped)
        self._canvas.node_deleted.connect(self._on_node_deleted)
        self._canvas.node_selected.connect(self._on_node_selected)
        self._canvas.edge_clicked.connect(self._on_edge_clicked)
        self._canvas.selection_cleared.connect(
            lambda: self._property_panel.set_node(None))

        # 属性面板信号
        self._property_panel.params_changed.connect(self._on_params_changed)
        self._property_panel.delete_node_requested.connect(
            self._on_node_deleted)
        self._property_panel.connect_requested.connect(
            self._on_connect_requested)

        # 模块库信号
        self._module_library.module_selected.connect(self._on_module_selected)
        self._module_library.module_add_requested.connect(self._on_new_module)
        self._module_library.module_edit_requested.connect(self._on_edit_module)
        self._module_library.module_delete_requested.connect(
            self._on_delete_module)
        self._module_library.module_duplicate_requested.connect(
            self._on_duplicate_module)

        # 电源树信号
        self._power_tree.tree_changed.connect(self._on_tree_changed)
        self._power_tree.calculation_updated.connect(
            self._property_panel.refresh_results)
        self._power_tree.calculation_updated.connect(self._update_status)
        self._power_tree.node_changed.connect(self._on_node_changed)

        # 项目管理器信号
        self._project_manager.project_modified.connect(
            self._on_project_modified)
        self._project_manager.recent_files_changed.connect(
            self._update_recent_menu)

    # ═══════════════════════════════════════════════════
    #  文件操作
    # ═══════════════════════════════════════════════════

    def _on_new_project(self) -> None:
        if self._project_manager.is_modified:
            reply = self._confirm_save()
            if reply == QMessageBox.StandardButton.Cancel:
                return
        self._project_manager.new_project()
        self._canvas.clear_all()
        self._update_title()
        self._update_status()
        self._status_label.setText("新建项目")

    def _on_open_project(self) -> None:
        if self._project_manager.is_modified:
            reply = self._confirm_save()
            if reply == QMessageBox.StandardButton.Cancel:
                return

        path, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "",
            "电源树项目 (*.pwt);;所有文件 (*.*)")
        if path:
            self._canvas.clear_all()
            if self._project_manager.open(Path(path)):
                self._rebuild_canvas()
                self._update_title()
                self._update_status()
                self._canvas.fit_to_content()
                self._status_label.setText(f"已打开: {path}")

    def _on_save_project(self) -> bool:
        if self._project_manager.current_file:
            if self._project_manager.save():
                self._status_label.setText(f"已保存: {self._project_manager.current_file}")
                self._update_title()
                return True
        else:
            return self._on_save_as_project()
        return False

    def _on_save_as_project(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self, "另存为", "power_tree.pwt",
            "电源树项目 (*.pwt);;所有文件 (*.*)")
        if path:
            if self._project_manager.save_as(Path(path)):
                self._status_label.setText(f"已保存: {path}")
                self._update_title()
                return True
        return False

    def _on_export(self) -> None:
        """导出"""
        if not self._power_tree.nodes:
            QMessageBox.information(self, "提示", "请先创建电源树")
            return

        dlg = ExportDialog(self)
        if dlg.exec() != ExportDialog.DialogCode.Accepted:
            return

        export_path = dlg.export_path
        export_path.mkdir(parents=True, exist_ok=True)

        if dlg.export_csv:
            self._export_csv(export_path / "power_report.csv")
        if dlg.export_png:
            self._export_image(export_path / "power_tree.png")
        if dlg.export_svg:
            self._export_image(export_path / "power_tree.svg")

        QMessageBox.information(self, "导出完成",
                                f"文件已保存到:\n{export_path}")
        self._status_label.setText(f"已导出到: {export_path}")

    # ═══════════════════════════════════════════════════
    #  模块操作
    # ═══════════════════════════════════════════════════

    def _on_module_selected(self, mod: PowerModule) -> None:
        """点击模块库中的模块 — 在属性面板显示模块信息，并在状态栏提示操作"""
        self._property_panel.show_module_info(mod)
        self._status_label.setText(
            f"已选中模块: {mod.name} — "
            f"先点击画布上的父节点，再拖拽模块到画布以建立连接")

    def _on_new_module(self) -> None:
        dlg = ModuleEditorDialog(self._module_manager, parent=self)
        if dlg.exec() == ModuleEditorDialog.DialogCode.Accepted:
            self._power_tree.set_modules(self._module_manager.modules)
            self._status_label.setText("已创建新模块")

    def _on_edit_module(self, module_id: str) -> None:
        mod = self._module_manager.get_module(module_id)
        if mod:
            dlg = ModuleEditorDialog(self._module_manager, mod, parent=self)
            if dlg.exec() == ModuleEditorDialog.DialogCode.Accepted:
                self._power_tree.set_modules(self._module_manager.modules)
                self._status_label.setText(f"已更新模块: {mod.name}")

    def _on_delete_module(self, module_id: str) -> None:
        if self._module_manager.delete_module(module_id):
            self._power_tree.set_modules(self._module_manager.modules)
            self._status_label.setText("已删除模块")

    def _on_duplicate_module(self, module_id: str) -> None:
        from PySide6.QtWidgets import QInputDialog
        mod = self._module_manager.get_module(module_id)
        if not mod:
            return
        new_name, ok = QInputDialog.getText(
            self, "复制模块", "新模块名称:",
            text=f"{mod.name}_copy")
        if ok and new_name:
            if self._module_manager.duplicate_module(module_id, new_name):
                self._power_tree.set_modules(self._module_manager.modules)
                self._status_label.setText(f"已复制模块: {new_name}")

    def _on_import_module(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "导入模块", "",
            "JSON 文件 (*.json);;所有文件 (*.*)")
        if path:
            if self._module_manager.import_module(Path(path)):
                self._power_tree.set_modules(self._module_manager.modules)
                self._status_label.setText(f"已导入模块: {Path(path).stem}")

    def _on_export_module(self) -> None:
        node = self._power_tree.selected_node
        if not node or not node.module_id:
            QMessageBox.information(self, "提示", "请先选中一个节点")
            return
        path = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if path:
            self._module_manager.export_module(node.module_id, Path(path))
            self._status_label.setText(f"已导出模块到: {path}")

    # ═══════════════════════════════════════════════════
    #  树操作
    # ═══════════════════════════════════════════════════

    def _on_add_root_source(self) -> None:
        """添加根节点（输入电源）"""
        sources = self._module_manager.get_modules_by_type(ModuleType.INPUT_SOURCE)
        if not sources:
            QMessageBox.warning(self, "提示", "没有可用的输入电源模块，请先创建")
            return
        mod = sources[0]
        node = self._power_tree.add_node(mod, parent_id=None, pos_x=0, pos_y=0)
        self._canvas.add_node_item(node)
        self._canvas.auto_layout(self._power_tree.nodes)
        self._canvas.sync_edges(self._power_tree.nodes)
        self._power_tree.recalculate()
        self._status_label.setText(f"已添加根节点: {mod.name}")

    def _on_module_dropped(self, module_id: str, x: float, y: float) -> None:
        """模块拖放到画布 — 优先连接到选中的节点，否则作为独立节点"""
        mod = self._module_manager.get_module(module_id)
        if not mod:
            return

        # ── 确定父节点 ──
        parent_id = None

        # 输入电源：只能作为根节点
        if mod.type == ModuleType.INPUT_SOURCE:
            if self._power_tree.root:
                QMessageBox.information(self, "提示",
                    "只能有一个根节点（输入电源），请先删除现有根节点")
                return
            parent_id = None
        elif mod.type == ModuleType.LOAD:
            # 负载：如果选中了节点则连到选中节点，否则自动连到最后一个非负载节点
            sel = self._power_tree.selected_node
            if sel and sel.module_type != ModuleType.LOAD.value:
                parent_id = sel.id
            else:
                # 自动找非负载父节点
                candidates = [n for n in self._power_tree.nodes.values()
                              if n.module_type != ModuleType.LOAD.value]
                if candidates:
                    parent_id = candidates[-1].id  # 最后一个非负载节点
                else:
                    QMessageBox.information(self, "提示",
                        "请先添加输入电源或转换器节点")
                    return
        else:
            # 转换器：选中节点优先，否则自动连到根节点
            sel = self._power_tree.selected_node
            if sel and sel.module_type != ModuleType.LOAD.value:
                parent_id = sel.id
            elif self._power_tree.root:
                parent_id = self._power_tree.root.id
            else:
                QMessageBox.information(self, "提示",
                    "请先添加输入电源节点")
                return

        node = self._power_tree.add_node(mod, parent_id=parent_id,
                                          pos_x=x, pos_y=y)
        item = self._canvas.add_node_item(node)

        # 更新画布
        if parent_id:
            self._canvas.auto_layout(self._power_tree.nodes)
        else:
            # 未连接节点：放在画布一侧
            item.setPos(x, y)

        self._canvas.sync_edges(self._power_tree.nodes)
        self._power_tree.recalculate()

        # 选中新节点
        self._power_tree.select_node(node.id)
        self._on_node_selected(node.id)

        if parent_id:
            self._status_label.setText(f"已添加节点: {mod.name} (已连接)")
        else:
            self._status_label.setText(
                f"已添加节点: {mod.name} (未连接 — 请拖到已有节点上或右键设置连接)")

    def _on_edge_clicked(self, parent_id: str, child_id: str) -> None:
        """点击连线 — 删除父子连接关系"""
        child = self._power_tree.nodes.get(child_id)
        parent = self._power_tree.nodes.get(parent_id)
        if not child or not parent:
            return
        reply = QMessageBox.question(
            self, "删除连接",
            f"断开 \"{child.name}\" 与 \"{parent.name}\" 的连接？\n"
            f"子节点将变为未连接状态。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # 设置子节点的 parent 为 None
            if self._power_tree.set_parent(child_id, None):
                self._canvas.sync_edges(self._power_tree.nodes)
                self._canvas.auto_layout(self._power_tree.nodes)
                self._power_tree.recalculate()
                self._status_label.setText(
                    f"已断开连接: {child.name} <-/-> {parent.name}")

    def _on_node_deleted(self, node_id: str) -> None:
        """删除节点"""
        self._canvas.remove_node_item(node_id)
        self._power_tree.remove_node(node_id)
        self._canvas.sync_edges(self._power_tree.nodes)
        self._power_tree.recalculate()
        self._property_panel.set_node(None)
        self._status_label.setText("已删除节点")

    def _on_node_selected(self, node_id: str) -> None:
        """节点选中"""
        if not node_id:
            self._property_panel.set_node(None)
            self._power_tree.select_node(None)
            return
        node = self._power_tree.nodes.get(node_id)
        module = self._power_tree.get_module(node.module_id) if node else None
        self._property_panel.set_node(node, module)
        self._power_tree.select_node(node_id)

    def _on_connect_requested(self, child_node_id: str) -> None:
        """为未连接节点选择父节点"""
        child_node = self._power_tree.nodes.get(child_node_id)
        if not child_node:
            return

        # 收集可选父节点（非自身、非子孙、非 LOAD、非已连接的子孙）
        candidates = []
        for nid, node in self._power_tree.nodes.items():
            if nid == child_node_id:
                continue
            if node.module_type == ModuleType.LOAD.value:
                continue
            # 防止循环：不能连接到自己的子孙
            if self._power_tree._is_descendant(child_node_id, nid):
                continue
            candidates.append((node.name, nid))

        if not candidates:
            QMessageBox.information(self, "提示",
                "没有可用的父节点。请先添加一个输入电源或转换器节点。")
            return

        # 创建选择对话框
        from PySide6.QtWidgets import QInputDialog
        names = [f"{name} [{nid[:6]}...]" for name, nid in candidates]
        selected, ok = QInputDialog.getItem(
            self, "选择父节点",
            f"为 \"{child_node.name}\" 选择父节点:",
            names, 0, False)
        if not ok:
            return

        idx = names.index(selected)
        parent_id = candidates[idx][1]

        if self._power_tree.set_parent(child_node_id, parent_id):
            self._canvas.sync_edges(self._power_tree.nodes)
            self._canvas.auto_layout(self._power_tree.nodes)
            self._power_tree.recalculate()
            self._on_node_selected(child_node_id)
            self._status_label.setText(
                f"已连接: {child_node.name} -> {self._power_tree.nodes[parent_id].name}")

    def _on_params_changed(self, node_id: str, params: dict) -> None:
        """属性面板参数变更"""
        self._power_tree.update_node_params(node_id, **params)
        self._power_tree.recalculate()
        self._canvas.update_all_edges(self._power_tree.nodes)
        self._property_panel.refresh_results()
        self._status_label.setText("参数已更新")

    def _on_node_changed(self, node_id: str) -> None:
        """节点变更后刷新画布"""
        node = self._power_tree.nodes.get(node_id)
        if node:
            item = self._canvas.get_node_item(node_id)
            if item:
                item.update()

    def _on_tree_changed(self) -> None:
        """树结构变更"""
        self._update_status()

    def _on_project_modified(self, modified: bool) -> None:
        self._update_title()

    def _on_auto_layout(self) -> None:
        """自动布局"""
        if self._power_tree.nodes:
            self._canvas.auto_layout(self._power_tree.nodes)
            self._canvas.sync_edges(self._power_tree.nodes)
            self._canvas.fit_to_content()
            self._status_label.setText("自动布局完成")

    # ═══════════════════════════════════════════════════
    #  辅助方法
    # ═══════════════════════════════════════════════════

    def _rebuild_canvas(self) -> None:
        """根据 PowerTree 重建画布"""
        self._canvas.clear_all()
        # 先建立所有节点项
        for node in self._power_tree.nodes.values():
            self._canvas.add_node_item(node)
        # 再建立连线
        self._canvas.sync_edges(self._power_tree.nodes)
        self._power_tree.recalculate()

    def _update_title(self) -> None:
        title = "电源树设计器 - Power Tree Designer"
        name = self._project_manager.project_name
        star = " *" if self._project_manager.is_modified else ""
        self.setWindowTitle(f"{title} [{name}{star}]")

    def _update_status(self) -> None:
        """更新状态栏摘要"""
        if not self._power_tree.nodes:
            self._summary_label.setText("")
            return
        from src.core.calculator import Calculator
        summary = Calculator.get_system_summary(self._power_tree.nodes)
        self._summary_label.setText(
            f"节点: {summary['num_nodes']} | "
            f"轨: {summary['num_rails']} | "
            f"总输入: {summary['total_input_power']:.2f}W | "
            f"总效率: {summary['system_efficiency'] * 100:.1f}% | "
            f"总损耗: {summary['total_power_loss']:.2f}W"
        )

    def _update_recent_menu(self) -> None:
        """更新最近打开文件菜单"""
        self._recent_menu.clear()
        for fpath in self._project_manager.get_recent_files():
            act = QAction(fpath.name, self)
            act.setToolTip(str(fpath))
            act.triggered.connect(
                lambda checked, p=fpath: self._open_recent(p))
            self._recent_menu.addAction(act)
        if self._recent_menu.isEmpty():
            self._recent_menu.addAction("(无)").setEnabled(False)
        else:
            self._recent_menu.addSeparator()
            clear_act = QAction("清除列表", self)
            clear_act.triggered.connect(
                self._project_manager.clear_recent_files)
            self._recent_menu.addAction(clear_act)

    def _open_recent(self, fpath: Path) -> None:
        if self._project_manager.is_modified:
            reply = self._confirm_save()
            if reply == QMessageBox.StandardButton.Cancel:
                return
        self._canvas.clear_all()
        if self._project_manager.open(fpath):
            self._rebuild_canvas()
            self._update_title()
            self._update_status()
            self._canvas.fit_to_content()

    def _confirm_save(self) -> QMessageBox.StandardButton:
        """询问是否保存修改"""
        reply = QMessageBox.question(
            self, "未保存的修改",
            "当前项目有未保存的修改，是否保存？",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel)
        if reply == QMessageBox.StandardButton.Save:
            if not self._on_save_project():
                return QMessageBox.StandardButton.Cancel
        return reply

    def _export_csv(self, filepath: Path) -> None:
        """导出 CSV 报表"""
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "节点ID", "名称", "类型", "输入电压(V)", "输出电压(V)",
                "输出电流(A)", "输入电流(A)", "输入功率(W)", "输出功率(W)",
                "功率损耗(W)", "效率(%)", "父节点ID"
            ])
            for node in self._power_tree.nodes.values():
                writer.writerow([
                    node.id, node.name, node.module_type,
                    f"{node.input_voltage:.2f}", f"{node.output_voltage:.2f}",
                    f"{node.output_current:.3f}", f"{node.input_current:.3f}",
                    f"{node.input_power:.3f}", f"{node.output_power:.3f}",
                    f"{node.power_loss:.3f}", f"{node.actual_efficiency * 100:.1f}",
                    node.parent_id or ""
                ])

    def _export_image(self, filepath: Path) -> None:
        """导出画布为图片"""
        from PySide6.QtGui import QPixmap
        pixmap = self._canvas.grab()
        pixmap.save(str(filepath))

    def _on_about(self) -> None:
        QMessageBox.about(
            self, "关于 电源树设计器",
            "<h3>电源树设计器 Power Tree Designer</h3>"
            "<p>版本 1.0.0</p>"
            "<p>一款用于电源树设计、计算和可视化的桌面工具。</p>"
            "<p>基于 Python + PySide6 开发。</p>"
            "<hr>"
            "<p>功能：</p>"
            "<ul>"
            "<li>拖放式电源树拓扑图设计</li>"
            "<li>自定义电源模块参数 (JSON)</li>"
            "<li>实时功率计算（效率/损耗/电流）</li>"
            "<li>项目保存/加载 (.pwt)</li>"
            "<li>导出计算结果和图形</li>"
            "</ul>"
        )

    # ═══════════════════════════════════════════════════
    #  关闭事件
    # ═══════════════════════════════════════════════════

    def closeEvent(self, event) -> None:
        if self._project_manager.is_modified:
            reply = self._confirm_save()
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        event.accept()
