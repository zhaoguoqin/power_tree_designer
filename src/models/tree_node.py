"""电源树节点数据模型"""

import uuid
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.power_module import PowerModule


@dataclass
class TreeNode:
    """电源树中的一个节点"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    module_id: str = ""                    # 关联的电源模块 ID
    name: str = ""                         # 节点显示名称
    module_type: str = ""                  # 模块类型字符串
    type_display: str = ""                 # 类型显示名（支持自定义）
    chip_name: str = ""                    # 芯片型号

    # 用户可设置的电气参数
    input_voltage: float = 0.0             # 输入电压 (V)
    output_voltage: float = 0.0            # 输出电压 (V) — 可覆盖模块默认值
    output_current: float = 0.0            # 输出电流 (A) — 负载电流
    efficiency_override: Optional[float] = None  # 手动覆盖效率 (None=使用模块默认)

    # 运行时计算结果
    input_current: float = 0.0             # 输入电流 (A)
    input_power: float = 0.0               # 输入功率 (W)
    output_power: float = 0.0              # 输出功率 (W)
    power_loss: float = 0.0                # 功率损耗 (W)
    actual_efficiency: float = 0.0         # 实际效率

    # 树结构
    parent_id: Optional[str] = None
    children_ids: list[str] = field(default_factory=list)

    # 画布位置
    pos_x: float = 0.0
    pos_y: float = 0.0

    def to_dict(self) -> dict:
        """序列化"""
        return {
            "id": self.id,
            "module_id": self.module_id,
            "name": self.name,
            "module_type": self.module_type,
            "type_display": self.type_display,
            "chip_name": self.chip_name,
            "input_voltage": self.input_voltage,
            "output_voltage": self.output_voltage,
            "output_current": self.output_current,
            "efficiency_override": self.efficiency_override,
            "input_current": self.input_current,
            "input_power": self.input_power,
            "output_power": self.output_power,
            "power_loss": self.power_loss,
            "actual_efficiency": self.actual_efficiency,
            "parent_id": self.parent_id,
            "children_ids": list(self.children_ids),
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TreeNode":
        """反序列化"""
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})

    @property
    def is_root(self) -> bool:
        return self.parent_id is None

    @property
    def is_leaf(self) -> bool:
        return len(self.children_ids) == 0
