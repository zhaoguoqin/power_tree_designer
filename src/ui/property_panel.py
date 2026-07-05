"""属性面板 — 编辑选中节点的参数"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QFormLayout,
    QGroupBox, QPushButton, QHBoxLayout, QDoubleSpinBox,
    QComboBox, QScrollArea, QFrame, QCheckBox, QMessageBox,
    QSizePolicy
)

from src.models.tree_node import TreeNode
from src.models.power_module import PowerModule, ModuleType


class PropertyPanel(QWidget):
    """节点属性编辑面板"""

    params_changed = Signal(str, dict)    # node_id, {key: value}
    recalculate_requested = Signal()
    delete_node_requested = Signal(str)   # node_id
    connect_requested = Signal(str)       # node_id (request to connect to a parent)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._node: Optional[TreeNode] = None
        self._module: Optional[PowerModule] = None
        self._widgets: dict[str, QWidget] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 4)
        layout.setSpacing(4)

        # 标题 — 始终在顶部
        self._title_label = QLabel("属性面板")
        title_font = QFont("Microsoft YaHei", 11)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._title_label.setStyleSheet("color: #333; padding: 2px 0;")
        layout.addWidget(self._title_label)

        # 滚动区域
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(8)

        # ── 基本信息组 ──
        self._basic_group = QGroupBox("基本信息")
        self._basic_form = QFormLayout(self._basic_group)
        self._basic_form.setSpacing(6)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("节点名称")
        self._basic_form.addRow("名称:", self._name_edit)
        self._widgets["name"] = self._name_edit

        self._type_label = QLabel("-")
        self._basic_form.addRow("类型:", self._type_label)

        self._module_label = QLabel("-")
        self._module_label.setWordWrap(True)
        self._basic_form.addRow("模块:", self._module_label)

        self._chip_name_edit = QLineEdit()
        self._chip_name_edit.setPlaceholderText("芯片型号，如 LMS1117")
        self._basic_form.addRow("芯片:", self._chip_name_edit)
        self._widgets["chip_name"] = self._chip_name_edit

        self._content_layout.addWidget(self._basic_group)

        # ── 电气参数组 ──
        self._elec_group = QGroupBox("电气参数")
        self._elec_form = QFormLayout(self._elec_group)
        self._elec_form.setSpacing(6)

        self._vin_label = QLabel("输入电压:")
        self._vin_spin = QDoubleSpinBox()
        self._vin_spin.setRange(0, 1000)
        self._vin_spin.setDecimals(2)
        self._vin_spin.setSuffix(" V")
        self._elec_form.addRow(self._vin_label, self._vin_spin)
        self._widgets["input_voltage"] = self._vin_spin

        self._vout_label = QLabel("输出电压:")
        self._vout_spin = QDoubleSpinBox()
        self._vout_spin.setRange(0, 1000)
        self._vout_spin.setDecimals(2)
        self._vout_spin.setSuffix(" V")
        self._elec_form.addRow(self._vout_label, self._vout_spin)
        self._widgets["output_voltage"] = self._vout_spin

        self._iout_label = QLabel("输出电流:")
        self._iout_spin = QDoubleSpinBox()
        self._iout_spin.setRange(0, 100)
        self._iout_spin.setDecimals(3)
        self._iout_spin.setSuffix(" A")
        self._iout_spin.setSingleStep(0.1)
        self._elec_form.addRow(self._iout_label, self._iout_spin)
        self._widgets["output_current"] = self._iout_spin

        self._eff_override = QCheckBox("手动覆盖效率")
        self._eff_spin = QDoubleSpinBox()
        self._eff_spin.setRange(1, 100)
        self._eff_spin.setDecimals(1)
        self._eff_spin.setSuffix(" %")
        self._eff_spin.setValue(90)
        self._eff_spin.setEnabled(False)
        self._elec_form.addRow(self._eff_override, self._eff_spin)
        self._widgets["efficiency_override"] = self._eff_spin

        self._content_layout.addWidget(self._elec_group)

        # ── 计算结果组 ──
        self._result_group = QGroupBox("计算结果")
        self._result_form = QFormLayout(self._result_group)
        self._result_form.setSpacing(4)

        self._result_labels: dict[str, QLabel] = {}
        for key, label in [
            ("input_current", "输入电流:"),
            ("input_power", "输入功率:"),
            ("output_power", "输出功率:"),
            ("power_loss", "功率损耗:"),
            ("actual_efficiency", "实际效率:"),
        ]:
            lbl = QLabel("-")
            lbl.setStyleSheet("color: #1565C0; font-weight: bold;")
            self._result_form.addRow(label, lbl)
            self._result_labels[key] = lbl

        self._content_layout.addWidget(self._result_group)

        # ── 操作按钮 ──
        self._btn_group = QGroupBox("操作")
        btn_layout = QHBoxLayout(self._btn_group)
        btn_layout.setSpacing(6)

        self._apply_btn = QPushButton("应用")
        self._apply_btn.setToolTip("应用参数修改并重新计算")
        self._connect_btn = QPushButton("连接到父节点...")
        self._connect_btn.setToolTip("将此节点连接到选中的父节点")
        self._connect_btn.setVisible(False)
        self._delete_btn = QPushButton("删除节点")
        self._delete_btn.setStyleSheet(
            "QPushButton { color: #D32F2F; } "
            "QPushButton:hover { background-color: #FFEBEE; }"
        )

        btn_layout.addWidget(self._apply_btn)
        btn_layout.addWidget(self._connect_btn)
        btn_layout.addWidget(self._delete_btn)
        self._content_layout.addWidget(self._btn_group)

        # 占位伸缩
        self._content_layout.addStretch()

        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll, 1)

        # ── 空状态 ──
        self._empty_label = QLabel("选择一个节点以编辑属性")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: #999; font-size: 12px;")
        layout.addWidget(self._empty_label)

        # 初始显示空状态
        self._scroll.hide()

        # ── 连接信号 ──
        self._apply_btn.clicked.connect(self._on_apply)
        self._connect_btn.clicked.connect(self._on_connect)
        self._delete_btn.clicked.connect(self._on_delete)
        self._eff_override.toggled.connect(self._eff_spin.setEnabled)

    def show_module_info(self, mod: PowerModule) -> None:
        """显示模块信息（只读预览，无节点时使用）"""
        self._node = None
        self._module = mod
        self._title_label.setText(f"模块信息: {mod.name}")

        self._scroll.show()
        self._empty_label.hide()

        # 隐藏编辑和结果组，只显示基本信息
        self._elec_group.hide()
        self._result_group.hide()
        self._btn_group.hide()

        self._basic_group.show()
        self._name_edit.blockSignals(True)
        self._name_edit.setText(mod.name)
        self._name_edit.setReadOnly(True)
        self._name_edit.blockSignals(False)
        type_disp = mod.type_display or self._type_display(
            mod.type.value if isinstance(mod.type, ModuleType) else mod.type)
        self._type_label.setText(type_disp)
        info_lines = []
        if mod.chip_name:
            info_lines.append(f"Chip: {mod.chip_name}")
        if mod.description:
            info_lines.append(mod.description)
        info_lines.append(f"Vin: {mod.input_voltage_min}~{mod.input_voltage_max}V")
        info_lines.append(f"Vout: {mod.output_voltage}V  "
                          f"Imax: {mod.max_output_current}A")
        info_lines.append(f"Eff: {mod.efficiency*100:.0f}%  "
                          f"Iq: {mod.quiescent_current_ma}mA")
        if mod.source_url:
            info_lines.append(f"Source: {mod.source_url}")
        self._module_label.setText("\n".join(info_lines))

    def set_node(self, node: Optional[TreeNode],
                 module: Optional[PowerModule] = None) -> None:
        """设置当前编辑的节点"""
        self._node = node
        self._module = module

        if node is None:
            self._title_label.setText("属性面板")
            self._scroll.hide()
            self._empty_label.show()
            return

        self._scroll.show()
        self._empty_label.hide()
        self._title_label.setText("属性面板")

        # 恢复节点编辑模式的所有组
        self._basic_group.show()
        self._elec_group.show()
        self._result_group.show()
        self._btn_group.show()
        self._name_edit.setReadOnly(False)

        # 阻断信号更新 UI
        self._name_edit.blockSignals(True)
        self._vin_spin.blockSignals(True)
        self._vout_spin.blockSignals(True)
        self._iout_spin.blockSignals(True)
        self._eff_spin.blockSignals(True)
        self._eff_override.blockSignals(True)

        self._name_edit.setText(node.name)
        type_disp = node.type_display or self._type_display(node.module_type)
        self._type_label.setText(type_disp)
        self._module_label.setText(module.name if module else "-")
        self._chip_name_edit.blockSignals(True)
        self._chip_name_edit.setText(node.chip_name)
        self._chip_name_edit.blockSignals(False)

        self._vin_spin.setValue(node.input_voltage)
        self._vout_spin.setValue(node.output_voltage)
        self._iout_spin.setValue(node.output_current)

        if node.efficiency_override is not None:
            self._eff_override.setChecked(True)
            self._eff_spin.setValue(node.efficiency_override * 100)
        else:
            self._eff_override.setChecked(False)
            self._eff_spin.setValue(
                module.efficiency * 100 if module else 90)

        # 根据类型调整可编辑性和标签
        is_source = node.module_type == ModuleType.INPUT_SOURCE.value
        is_load = node.module_type == ModuleType.LOAD.value

        if is_load:
            # 负载节点：只显示工作电压和负载电流
            self._vin_spin.hide()
            self._vin_label.hide()
            self._vout_label.setText("工作电压:")
            self._vout_spin.show()
            self._vout_spin.setEnabled(True)
            self._iout_label.setText("负载电流:")
            self._iout_spin.show()
            self._iout_spin.setEnabled(True)
            self._eff_override.hide()
            self._eff_spin.hide()
        elif is_source:
            # 输入电源：输入电压可编辑
            self._vin_label.setText("输入电压:")
            self._vin_spin.show()
            self._vin_spin.setEnabled(True)
            self._vout_label.setText("额定电压:")
            self._vout_spin.show()
            self._vout_spin.setEnabled(True)
            self._iout_label.setText("最大电流:")
            self._iout_spin.show()
            self._iout_spin.setEnabled(False)
            self._eff_override.hide()
            self._eff_spin.hide()
        else:
            # 转换器：输入电压由父节点决定（只读）
            self._vin_label.setText("输入电压(自动):")
            self._vin_spin.show()
            self._vin_spin.setEnabled(False)
            self._vout_label.setText("输出电压:")
            self._vout_spin.show()
            self._vout_spin.setEnabled(True)
            self._iout_label.setText("输出电流:")
            self._iout_spin.show()
            self._iout_spin.setEnabled(False)
            self._eff_override.show()
            self._eff_spin.setVisible(self._eff_override.isChecked())

        # 未连接节点显示"连接到父节点"按钮
        self._connect_btn.setVisible(node.parent_id is None and not is_source)

        self._update_results()

        self._name_edit.blockSignals(False)
        self._vin_spin.blockSignals(False)
        self._vout_spin.blockSignals(False)
        self._iout_spin.blockSignals(False)
        self._eff_spin.blockSignals(False)
        self._eff_override.blockSignals(False)

    def _update_results(self) -> None:
        """更新结果显示"""
        if self._node is None:
            return
        n = self._node
        self._result_labels["input_current"].setText(f"{n.input_current:.3f} A")
        self._result_labels["input_power"].setText(f"{n.input_power:.2f} W")
        self._result_labels["output_power"].setText(f"{n.output_power:.2f} W")
        self._result_labels["power_loss"].setText(
            f"{n.power_loss:.2f} W ({n.power_loss / n.input_power * 100:.1f}%)"
            if n.input_power > 0 else "0.00 W")
        self._result_labels["actual_efficiency"].setText(
            f"{n.actual_efficiency * 100:.1f}%")

    def refresh_results(self) -> None:
        """刷新计算结果（外部触发）"""
        self._update_results()

    def _on_apply(self) -> None:
        """应用修改"""
        if self._node is None:
            return

        # 验证
        vout = self._vout_spin.value()
        if self._module and not self._module.type == ModuleType.LOAD:
            if self._module.output_voltage_adj:
                vmin = self._module.output_voltage_min
                vmax = self._module.output_voltage_max
                if vout < vmin or vout > vmax:
                    QMessageBox.warning(self, "参数警告",
                        f"输出电压 {vout}V 超出模块可调范围 [{vmin}V, {vmax}V]")

        params = {
            "name": self._name_edit.text(),
            "chip_name": self._chip_name_edit.text().strip(),
            "input_voltage": self._vin_spin.value(),
            "output_voltage": vout,
            "output_current": self._iout_spin.value(),
            "efficiency_override": (
                self._eff_spin.value() / 100.0
                if self._eff_override.isChecked() else None
            ),
        }
        self.params_changed.emit(self._node.id, params)

    def _on_connect(self) -> None:
        """请求连接到父节点"""
        if self._node is None:
            return
        self.connect_requested.emit(self._node.id)

    def _on_delete(self) -> None:
        """删除节点"""
        if self._node is None:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除节点 \"{self._node.name}\" 及其所有子节点吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_node_requested.emit(self._node.id)

    @staticmethod
    def _type_display(mtype: str) -> str:
        names = {
            "input_source": "⚡ 输入电源",
            "buck": "⬇ Buck 降压",
            "boost": "⬆ Boost 升压",
            "buck_boost": "🔄 Buck-Boost 升降压",
            "ldo": "▬ LDO 线性稳压",
            "load": "📱 负载",
            "other": "❓ 其他",
        }
        return names.get(mtype, mtype)
