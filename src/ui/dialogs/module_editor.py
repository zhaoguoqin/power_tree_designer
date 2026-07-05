"""模块编辑器对话框"""

from typing import Optional, TYPE_CHECKING
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QDoubleSpinBox, QCheckBox,
    QTextEdit, QPushButton, QGroupBox, QLabel,
    QDialogButtonBox, QMessageBox, QWidget, QScrollArea,
    QFrame
)

from src.models.power_module import PowerModule, ModuleType

if TYPE_CHECKING:
    from src.core.module_manager import ModuleManager


class ModuleEditorDialog(QDialog):
    """电源模块编辑对话框"""

    def __init__(self, module_manager: "ModuleManager",
                 module: Optional[PowerModule] = None,
                 parent=None):
        super().__init__(parent)
        self._module_manager = module_manager
        self._module = module
        self._is_new = module is None

        self.setWindowTitle("新建模块" if self._is_new else f"编辑模块 - {module.name}")
        self.setMinimumSize(500, 550)
        self._setup_ui()

        if module:
            self._load_module(module)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)

        # ── 基本信息 ──
        basic_group = QGroupBox("基本信息")
        basic_form = QFormLayout(basic_group)
        basic_form.setSpacing(8)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("例如: BUCK_12V_to_5V_3A")
        basic_form.addRow("模块名称:", self._name_edit)

        self._type_combo = QComboBox()
        for mt in ModuleType:
            self._type_combo.addItem(
                f"{self._type_icon(mt)} {ModuleType.display_name(mt)}",
                mt.value)
        basic_form.addRow("模块类型:", self._type_combo)

        self._type_display_edit = QLineEdit()
        self._type_display_edit.setPlaceholderText("自定义类型名称（留空使用默认）")
        basic_form.addRow("自定义类型名:", self._type_display_edit)

        self._chip_name_edit = QLineEdit()
        self._chip_name_edit.setPlaceholderText("例如: LMS1117, TPS5430")
        basic_form.addRow("芯片型号:", self._chip_name_edit)

        self._desc_edit = QTextEdit()
        self._desc_edit.setMaximumHeight(60)
        self._desc_edit.setPlaceholderText("模块描述...")
        basic_form.addRow("描述:", self._desc_edit)

        self._source_url_edit = QLineEdit()
        self._source_url_edit.setPlaceholderText("数据手册链接 (URL)")
        basic_form.addRow("数据手册:", self._source_url_edit)

        content_layout.addWidget(basic_group)

        # ── 电气参数 ──
        elec_group = QGroupBox("电气参数")
        elec_form = QFormLayout(elec_group)
        elec_form.setSpacing(8)

        self._vin_min = QDoubleSpinBox()
        self._vin_min.setRange(0, 500)
        self._vin_min.setDecimals(2)
        self._vin_min.setSuffix(" V")
        elec_form.addRow("最小输入电压:", self._vin_min)

        self._vin_max = QDoubleSpinBox()
        self._vin_max.setRange(0, 500)
        self._vin_max.setDecimals(2)
        self._vin_max.setSuffix(" V")
        self._vin_max.setValue(12)
        elec_form.addRow("最大输入电压:", self._vin_max)

        self._vout_adj = QCheckBox("输出电压可调")
        elec_form.addRow("", self._vout_adj)

        self._vout_default = QDoubleSpinBox()
        self._vout_default.setRange(0, 500)
        self._vout_default.setDecimals(2)
        self._vout_default.setSuffix(" V")
        self._vout_default.setValue(5)
        elec_form.addRow("默认输出电压:", self._vout_default)

        self._vout_min = QDoubleSpinBox()
        self._vout_min.setRange(0, 500)
        self._vout_min.setDecimals(2)
        self._vout_min.setSuffix(" V")
        self._vout_min.setEnabled(False)
        elec_form.addRow("可调最小输出:", self._vout_min)

        self._vout_max = QDoubleSpinBox()
        self._vout_max.setRange(0, 500)
        self._vout_max.setDecimals(2)
        self._vout_max.setSuffix(" V")
        self._vout_max.setEnabled(False)
        elec_form.addRow("可调最大输出:", self._vout_max)

        self._vout_adj.toggled.connect(self._vout_min.setEnabled)
        self._vout_adj.toggled.connect(self._vout_max.setEnabled)

        self._imax = QDoubleSpinBox()
        self._imax.setRange(0, 100)
        self._imax.setDecimals(3)
        self._imax.setSuffix(" A")
        self._imax.setValue(1.0)
        elec_form.addRow("最大输出电流:", self._imax)

        self._eff = QDoubleSpinBox()
        self._eff.setRange(1, 100)
        self._eff.setDecimals(1)
        self._eff.setSuffix(" %")
        self._eff.setValue(90)
        elec_form.addRow("典型效率:", self._eff)

        self._iq = QDoubleSpinBox()
        self._iq.setRange(0, 100)
        self._iq.setDecimals(1)
        self._iq.setSuffix(" mA")
        elec_form.addRow("静态电流:", self._iq)

        self._category_edit = QLineEdit()
        self._category_edit.setPlaceholderText("自定义分类（留空使用默认）")
        elec_form.addRow("分类:", self._category_edit)

        content_layout.addWidget(elec_group)

        # ── 按钮 ──
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        content_layout.addWidget(btn_box)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _load_module(self, mod: PowerModule) -> None:
        """加载已有模块数据"""
        self._name_edit.setText(mod.name)
        idx = self._type_combo.findData(mod.type.value if isinstance(mod.type, ModuleType) else mod.type)
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        self._type_display_edit.setText(mod.type_display)
        self._chip_name_edit.setText(mod.chip_name)
        self._desc_edit.setText(mod.description)
        self._source_url_edit.setText(mod.source_url)
        self._vin_min.setValue(mod.input_voltage_min)
        self._vin_max.setValue(mod.input_voltage_max)
        self._vout_default.setValue(mod.output_voltage)
        self._vout_adj.setChecked(mod.output_voltage_adj)
        self._vout_min.setValue(mod.output_voltage_min)
        self._vout_max.setValue(mod.output_voltage_max)
        self._imax.setValue(mod.max_output_current)
        self._eff.setValue(mod.efficiency * 100)
        self._iq.setValue(mod.quiescent_current_ma)
        self._category_edit.setText(mod.category)

    def _on_accept(self) -> None:
        """保存"""
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "模块名称不能为空")
            return

        # 检查重名
        existing = self._module_manager.get_module_by_name(name)
        if existing and (self._is_new or existing.id != self._module.id):
            QMessageBox.warning(self, "错误",
                                f"模块名称 \"{name}\" 已存在，请使用其他名称")
            return

        mod = PowerModule(
            name=name,
            type=ModuleType(self._type_combo.currentData()),
            type_display=self._type_display_edit.text().strip(),
            chip_name=self._chip_name_edit.text().strip(),
            description=self._desc_edit.toPlainText().strip(),
            source_url=self._source_url_edit.text().strip(),
            input_voltage_min=self._vin_min.value(),
            input_voltage_max=self._vin_max.value(),
            output_voltage=self._vout_default.value(),
            output_voltage_adj=self._vout_adj.isChecked(),
            output_voltage_min=self._vout_min.value(),
            output_voltage_max=self._vout_max.value(),
            max_output_current=self._imax.value(),
            efficiency=self._eff.value() / 100.0,
            quiescent_current_ma=self._iq.value(),
            category=self._category_edit.text().strip() or (
                ModuleType.category_name(ModuleType(self._type_combo.currentData()))),
            id=self._module.id if self._module else "",
        )

        errors = mod.validate()
        if errors:
            QMessageBox.warning(self, "参数验证失败",
                                "\n".join(f"• {e}" for e in errors))
            return

        self._module_manager.save_module(mod)
        self.accept()

    @staticmethod
    def _type_icon(mt: ModuleType) -> str:
        icons = {
            ModuleType.INPUT_SOURCE: "⚡",
            ModuleType.BUCK: "⬇",
            ModuleType.BOOST: "⬆",
            ModuleType.BUCK_BOOST: "🔄",
            ModuleType.LDO: "▬",
            ModuleType.LOAD: "📱",
            ModuleType.OTHER: "❓",
        }
        return icons.get(mt, "❓")
