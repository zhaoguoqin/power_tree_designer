"""功率计算引擎 — 前向传播和后向传播"""

import math
from typing import Optional
from src.models.power_module import PowerModule, ModuleType
from src.models.tree_node import TreeNode


class Calculator:
    """电源树功率计算引擎"""

    @staticmethod
    def calculate_forward(node_map: dict[str, TreeNode],
                          modules: dict[str, PowerModule]) -> None:
        """前向传播：从根到叶计算每个节点的输入电压（等于父节点输出电压）"""
        # 找到根节点
        roots = [n for n in node_map.values() if n.is_root]
        for root in roots:
            Calculator._propagate_voltage(root, node_map)

    @staticmethod
    def _propagate_voltage(node: TreeNode,
                           node_map: dict[str, TreeNode],
                           parent_voltage: Optional[float] = None) -> None:
        """递归传播电压"""
        if parent_voltage is not None:
            node.input_voltage = parent_voltage
        for child_id in node.children_ids:
            child = node_map.get(child_id)
            if child:
                Calculator._propagate_voltage(child, node_map, node.output_voltage)

    @staticmethod
    def calculate_backward(node_map: dict[str, TreeNode],
                           modules: dict[str, PowerModule]) -> dict:
        """后向传播：从叶到根计算功率、电流、损耗"""
        leaves = [n for n in node_map.values() if n.is_leaf]
        visited: set[str] = set()

        def calc_node(node_id: str) -> dict:
            """递归计算单个节点的功率，返回 {output_power, input_power, ...}"""
            if node_id in visited:
                return {}
            visited.add(node_id)

            node = node_map[node_id]
            mod = modules.get(node.module_id)

            # 1. 如果是叶子节点（load），直接使用设置的输出电流
            if node.is_leaf:
                node.output_power = node.output_voltage * node.output_current
            else:
                # 父节点：输出功率 = 所有子节点输入功率之和
                total_child_input_power = 0.0
                for child_id in node.children_ids:
                    calc_node(child_id)
                    child = node_map.get(child_id)
                    if child:
                        total_child_input_power += child.input_power
                node.output_power = total_child_input_power
                node.output_current = (
                    node.output_power / node.output_voltage
                    if node.output_voltage > 0 else 0.0
                )

            # 2. 获取效率
            if node.efficiency_override is not None:
                eff = node.efficiency_override
            elif mod:
                load_ratio = (node.output_current / mod.max_output_current
                              if mod.max_output_current > 0 else 1.0)
                eff = mod.get_efficiency(min(load_ratio, 1.0))
            else:
                eff = 0.90

            node.actual_efficiency = eff

            # 3. 计算输入功率
            if node.module_type == ModuleType.INPUT_SOURCE.value:
                # 输入电源：假设效率 100%（实际损耗在外部分析）
                node.input_power = node.output_power
                node.power_loss = 0.0
                node.input_current = (
                    node.input_power / node.input_voltage
                    if node.input_voltage > 0 else 0.0
                )
            else:
                node.input_power = (
                    node.output_power / eff if eff > 0 else node.output_power
                )
                node.power_loss = node.input_power - node.output_power
                node.input_current = (
                    node.input_power / node.input_voltage
                    if node.input_voltage > 0 else 0.0
                )

            # 4. LDO 特殊处理 (仅在未手动覆盖效率时生效)
            if mod and mod.type == ModuleType.LDO and node.efficiency_override is None:
                i_q = mod.quiescent_current_ma / 1000.0  # mA -> A
                node.input_current = node.output_current + i_q
                node.input_power = node.input_voltage * node.input_current
                node.power_loss = node.input_power - node.output_power
                node.actual_efficiency = (
                    node.output_power / node.input_power
                    if node.input_power > 0 else 0.0
                )

            return {
                "output_power": node.output_power,
                "input_power": node.input_power,
                "power_loss": node.power_loss,
                "efficiency": node.actual_efficiency,
            }

        results = {}
        for leaf in leaves:
            results[leaf.id] = calc_node(leaf.id)

        # 确保所有节点都被计算（包括中间节点）
        for node_id in node_map:
            if node_id not in visited:
                results[node_id] = calc_node(node_id)

        return results

    @staticmethod
    def calculate_all(node_map: dict[str, TreeNode],
                      modules: dict[str, PowerModule]) -> dict:
        """执行完整计算（前向 + 后向传播）"""
        Calculator.calculate_forward(node_map, modules)
        return Calculator.calculate_backward(node_map, modules)

    @staticmethod
    def get_system_summary(node_map: dict[str, TreeNode]) -> dict:
        """获取系统总体摘要"""
        roots = [n for n in node_map.values() if n.is_root]
        leaves = [n for n in node_map.values() if n.is_leaf]
        if not roots:
            return {
                "total_input_power": 0.0,
                "total_output_power": 0.0,
                "total_power_loss": 0.0,
                "system_efficiency": 0.0,
                "num_nodes": len(node_map),
                "num_rails": len(leaves),
            }

        # Total input power = sum of all root input powers (from the real supply)
        total_input_power = sum(r.input_power for r in roots)

        # Total useful output power = sum of all leaf (load) output powers
        total_output_power = sum(n.output_power for n in leaves)

        # Total system loss (all nodes)
        total_power_loss = sum(n.power_loss for n in node_map.values())
        system_efficiency = (
            total_output_power / total_input_power
            if total_input_power > 0 else 0.0
        )

        return {
            "total_input_power": total_input_power,
            "total_output_power": total_output_power,
            "total_power_loss": total_power_loss,
            "system_efficiency": system_efficiency,
            "num_nodes": len(node_map),
            "num_rails": len(leaves),
        }
