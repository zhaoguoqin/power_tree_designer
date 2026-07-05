"""电源模块数据模型"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


class ModuleType(str, Enum):
    """电源模块类型"""
    INPUT_SOURCE = "input_source"       # 输入电源
    BUCK = "buck"                       # 降压转换器
    BOOST = "boost"                     # 升压转换器
    BUCK_BOOST = "buck_boost"          # 升降压转换器
    LDO = "ldo"                         # 线性稳压器
    LOAD = "load"                       # 负载
    OTHER = "other"                     # 其他

    @classmethod
    def display_name(cls, mt: "ModuleType") -> str:
        names = {
            cls.INPUT_SOURCE: "输入电源",
            cls.BUCK: "Buck 降压",
            cls.BOOST: "Boost 升压",
            cls.BUCK_BOOST: "Buck-Boost 升降压",
            cls.LDO: "LDO 线性稳压",
            cls.LOAD: "负载",
            cls.OTHER: "其他",
        }
        return names.get(mt, str(mt))

    @classmethod
    def category_name(cls, mt: "ModuleType") -> str:
        """用于模块库分类"""
        categories = {
            cls.INPUT_SOURCE: "输入电源",
            cls.BUCK: "Buck 降压转换器",
            cls.BOOST: "Boost 升压转换器",
            cls.BUCK_BOOST: "Buck-Boost 升降压",
            cls.LDO: "LDO 线性稳压器",
            cls.LOAD: "负载",
            cls.OTHER: "其他",
        }
        return categories.get(mt, "其他")


# ── 可自定义的类型 ──────────────────────────────────

PRESET_TYPES = {
    "input_source": "输入电源",
    "buck": "Buck 降压",
    "boost": "Boost 升压",
    "buck_boost": "Buck-Boost 升降压",
    "ldo": "LDO 线性稳压",
    "load": "负载",
    "other": "其他",
}


def get_type_display(type_str: str) -> str:
    """获取类型的显示名称（支持自定义类型）"""
    return PRESET_TYPES.get(type_str, type_str)


@dataclass
class EfficiencyPoint:
    """效率曲线上的一个点"""
    load_ratio: float   # 负载比例 0.0 ~ 1.0
    efficiency: float   # 效率 0.0 ~ 1.0

    def to_list(self) -> list[float]:
        return [self.load_ratio, self.efficiency]

    @classmethod
    def from_list(cls, data: list[float]) -> "EfficiencyPoint":
        return cls(load_ratio=data[0], efficiency=data[1])


@dataclass
class PowerModule:
    """电源模块定义"""
    name: str                            # 模块名称
    type: ModuleType                     # 模块类型
    type_display: str = ""               # 自定义类型显示名（为空则用预设）
    chip_name: str = ""                  # 芯片型号（如 LMS1117）
    description: str = ""                # 描述
    source_url: str = ""                 # 数据手册/来源网址
    input_voltage_min: float = 0.0       # 最小输入电压 (V)
    input_voltage_max: float = 0.0       # 最大输入电压 (V)
    output_voltage: float = 0.0          # 默认输出电压 (V)
    output_voltage_adj: bool = False     # 输出电压是否可调
    output_voltage_min: float = 0.0      # 可调最小输出电压
    output_voltage_max: float = 0.0      # 可调最大输出电压
    max_output_current: float = 0.0      # 最大输出电流 (A)
    efficiency: float = 0.90             # 典型效率 (0~1)
    efficiency_curve: list = field(default_factory=list)  # [[load_ratio, eff], ...]
    quiescent_current_ma: float = 0.0    # 静态电流 (mA)
    category: str = ""                   # 分类标签
    tags: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def get_efficiency(self, load_ratio: float = 1.0) -> float:
        """根据负载比例获取效率（支持效率曲线插值）"""
        if not self.efficiency_curve:
            return self.efficiency
        curve = sorted(self.efficiency_curve, key=lambda p: p[0])
        if load_ratio <= curve[0][0]:
            return curve[0][1]
        if load_ratio >= curve[-1][0]:
            return curve[-1][1]
        for i in range(len(curve) - 1):
            r1, e1 = curve[i]
            r2, e2 = curve[i + 1]
            if r1 <= load_ratio <= r2:
                t = (load_ratio - r1) / (r2 - r1) if r2 != r1 else 0
                return e1 + t * (e2 - e1)
        return self.efficiency

    def to_dict(self) -> dict:
        """序列化为字典"""
        d = asdict(self)
        d["type"] = self.type.value if isinstance(self.type, ModuleType) else self.type
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PowerModule":
        """从字典反序列化"""
        data = dict(data)
        data["type"] = ModuleType(data["type"])
        if "id" not in data:
            data["id"] = str(uuid.uuid4())[:8]
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})

    def save_to_file(self, filepath: Path) -> None:
        """保存为 JSON 文件"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_file(cls, filepath: Path) -> "PowerModule":
        """从 JSON 文件加载"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def validate(self) -> list[str]:
        """验证参数合理性，返回错误信息列表"""
        errors = []
        if not self.name.strip():
            errors.append("模块名称不能为空")
        if self.input_voltage_max < self.input_voltage_min:
            errors.append("最大输入电压不能小于最小输入电压")
        if self.output_voltage_adj:
            if self.output_voltage_max < self.output_voltage_min:
                errors.append("可调输出电压范围无效")
        if self.max_output_current <= 0 and self.type != ModuleType.LOAD:
            errors.append("最大输出电流必须大于 0")
        if not 0 < self.efficiency <= 1:
            errors.append("效率必须在 (0, 1] 范围内")
        for pt in self.efficiency_curve:
            if not (0 <= pt[0] <= 1 and 0 < pt[1] <= 1):
                errors.append(f"效率曲线点 [{pt[0]}, {pt[1]}] 无效")
        return errors
