"""Calculator engine tests"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.power_module import PowerModule, ModuleType
from src.models.tree_node import TreeNode
from src.core.calculator import Calculator


def create_test_module(name: str, mtype: ModuleType, vout: float,
                       imax: float, eff: float) -> PowerModule:
    return PowerModule(
        name=name,
        type=mtype,
        output_voltage=vout,
        max_output_current=imax,
        efficiency=eff,
        input_voltage_min=0,
        input_voltage_max=100,
    )


def test_simple_tree():
    """Test: 12V -> Buck(5V/90%) -> Load(5V, 1A)"""
    mod_input = create_test_module("12V_IN", ModuleType.INPUT_SOURCE, 12.0, 10, 1.0)
    mod_buck = create_test_module("BUCK_5V", ModuleType.BUCK, 5.0, 3, 0.90)
    mod_load = create_test_module("LOAD", ModuleType.LOAD, 5.0, 5, 1.0)

    root = TreeNode(module_id=mod_input.id, name="12V_IN",
                    module_type="input_source",
                    input_voltage=12.0, output_voltage=12.0, output_current=0)
    buck = TreeNode(module_id=mod_buck.id, name="BUCK_5V",
                    module_type="buck", parent_id=root.id,
                    input_voltage=12.0, output_voltage=5.0, output_current=0)
    load = TreeNode(module_id=mod_load.id, name="LOAD",
                    module_type="load", parent_id=buck.id,
                    input_voltage=5.0, output_voltage=5.0, output_current=1.0)

    root.children_ids = [buck.id]
    buck.children_ids = [load.id]

    node_map = {root.id: root, buck.id: buck, load.id: load}
    modules = {mod_input.id: mod_input, mod_buck.id: mod_buck, mod_load.id: mod_load}

    result = Calculator.calculate_all(node_map, modules)

    assert abs(load.output_power - 5.0) < 0.01, f"Load P_out error: {load.output_power}"
    assert abs(load.input_power - 5.0) < 0.01, f"Load P_in error: {load.input_power}"

    # Buck: P_out ~5W, P_in = 5W / 0.9 ~5.556W
    assert abs(buck.output_power - 5.0) < 0.1, f"Buck P_out error: {buck.output_power}"
    assert abs(buck.input_power - 5.555) < 0.1, f"Buck P_in error: {buck.input_power}"
    assert abs(buck.power_loss - 0.555) < 0.1, f"Buck P_loss error: {buck.power_loss}"

    # Input: P_out ~5.556W
    assert abs(root.output_power - 5.555) < 0.1, f"Root P_out error: {root.output_power}"

    print("[PASS] test_simple_tree")
    return True


def test_buck_ldo_chain():
    """Test: 12V -> Buck(5V/90%) -> LDO(3.3V/66%) -> Load(100mA)"""
    mod_input = create_test_module("12V_IN", ModuleType.INPUT_SOURCE, 12.0, 10, 1.0)
    mod_buck = create_test_module("BUCK", ModuleType.BUCK, 5.0, 3, 0.90)
    mod_ldo = create_test_module("LDO", ModuleType.LDO, 3.3, 1, 0.66)
    mod_ldo.quiescent_current_ma = 2.0
    mod_load = create_test_module("MCU", ModuleType.LOAD, 3.3, 1, 1.0)

    root = TreeNode(module_id=mod_input.id, name="12V_IN",
                    module_type="input_source",
                    input_voltage=12.0, output_voltage=12.0, output_current=0)
    buck = TreeNode(module_id=mod_buck.id, name="BUCK",
                    module_type="buck", parent_id=root.id,
                    input_voltage=12.0, output_voltage=5.0, output_current=0)
    ldo = TreeNode(module_id=mod_ldo.id, name="LDO",
                   module_type="ldo", parent_id=buck.id,
                   input_voltage=5.0, output_voltage=3.3, output_current=0)
    load = TreeNode(module_id=mod_load.id, name="MCU",
                    module_type="load", parent_id=ldo.id,
                    input_voltage=3.3, output_voltage=3.3, output_current=0.1)

    root.children_ids = [buck.id]
    buck.children_ids = [ldo.id]
    ldo.children_ids = [load.id]

    node_map = {root.id: root, buck.id: buck, ldo.id: ldo, load.id: load}
    modules = {mod_input.id: mod_input, mod_buck.id: mod_buck,
               mod_ldo.id: mod_ldo, mod_load.id: mod_load}

    result = Calculator.calculate_all(node_map, modules)

    # Load: P_out = 3.3V * 0.1A = 0.33W
    assert abs(load.output_power - 0.33) < 0.01, f"Load P_out error: {load.output_power}"

    # LDO: P_out ~0.33W, P_in should be larger (dropout loss)
    assert ldo.power_loss > 0, "LDO should have power loss"
    assert ldo.input_power > ldo.output_power, "LDO P_in > P_out"

    print(f"  Load P_out={load.output_power:.3f}W")
    print(f"  LDO P_in={ldo.input_power:.3f}W, P_loss={ldo.power_loss:.3f}W")
    print(f"  Buck P_in={buck.input_power:.3f}W, P_loss={buck.power_loss:.3f}W")
    print(f"  System total input: {root.output_power:.3f}W")
    print("[PASS] test_buck_ldo_chain")
    return True


def test_forward_voltage_propagation():
    """Test forward voltage propagation"""
    mod_input = create_test_module("12V_IN", ModuleType.INPUT_SOURCE, 12.0, 10, 1.0)
    mod_buck = create_test_module("BUCK", ModuleType.BUCK, 5.0, 3, 0.90)
    mod_load = create_test_module("LOAD", ModuleType.LOAD, 3.3, 1, 1.0)

    root = TreeNode(module_id=mod_input.id, name="12V",
                    module_type="input_source",
                    input_voltage=12.0, output_voltage=12.0, output_current=0)
    buck = TreeNode(module_id=mod_buck.id, name="BUCK",
                    module_type="buck", parent_id=root.id,
                    input_voltage=0, output_voltage=5.0, output_current=0)
    load = TreeNode(module_id=mod_load.id, name="LOAD",
                    module_type="load", parent_id=buck.id,
                    input_voltage=0, output_voltage=3.3, output_current=0.5)

    root.children_ids = [buck.id]
    buck.children_ids = [load.id]

    node_map = {root.id: root, buck.id: buck, load.id: load}
    modules = {mod_input.id: mod_input, mod_buck.id: mod_buck, mod_load.id: mod_load}

    Calculator.calculate_forward(node_map, modules)

    # Buck should receive 12V
    assert abs(buck.input_voltage - 12.0) < 0.01, f"Buck Vin error: {buck.input_voltage}"
    # Load should receive 5V
    assert abs(load.input_voltage - 5.0) < 0.01, f"Load Vin error: {load.input_voltage}"

    print("[PASS] test_forward_voltage_propagation")
    return True


def test_system_summary():
    """Test system summary"""
    mod_input = create_test_module("24V_IN", ModuleType.INPUT_SOURCE, 24.0, 5, 1.0)
    mod_buck1 = create_test_module("BUCK1", ModuleType.BUCK, 5.0, 2, 0.90)
    mod_buck2 = create_test_module("BUCK2", ModuleType.BUCK, 3.3, 1, 0.88)
    mod_load1 = create_test_module("L1", ModuleType.LOAD, 5.0, 2, 1.0)
    mod_load2 = create_test_module("L2", ModuleType.LOAD, 3.3, 1, 1.0)

    root = TreeNode(module_id=mod_input.id, name="24V",
                    module_type="input_source",
                    input_voltage=24, output_voltage=24, output_current=0)
    b1 = TreeNode(module_id=mod_buck1.id, name="B1", module_type="buck",
                  parent_id=root.id,
                  input_voltage=24, output_voltage=5, output_current=0)
    b2 = TreeNode(module_id=mod_buck2.id, name="B2", module_type="buck",
                  parent_id=root.id,
                  input_voltage=24, output_voltage=3.3, output_current=0)
    l1 = TreeNode(module_id=mod_load1.id, name="L1", module_type="load",
                  parent_id=b1.id,
                  input_voltage=5, output_voltage=5, output_current=1.0)
    l2 = TreeNode(module_id=mod_load2.id, name="L2", module_type="load",
                  parent_id=b2.id,
                  input_voltage=3.3, output_voltage=3.3, output_current=0.5)

    root.children_ids = [b1.id, b2.id]
    b1.children_ids = [l1.id]
    b2.children_ids = [l2.id]

    node_map = {root.id: root, b1.id: b1, b2.id: b2, l1.id: l1, l2.id: l2}
    modules = {mod_input.id: mod_input, mod_buck1.id: mod_buck1,
               mod_buck2.id: mod_buck2, mod_load1.id: mod_load1,
               mod_load2.id: mod_load2}

    Calculator.calculate_all(node_map, modules)
    summary = Calculator.get_system_summary(node_map)

    assert summary["num_nodes"] == 5
    assert summary["num_rails"] == 2   # L1, L2
    assert summary["total_power_loss"] > 0
    assert 0 < summary["system_efficiency"] <= 1

    print(f"  Nodes: {summary['num_nodes']}, Rails: {summary['num_rails']}")
    print(f"  Total input: {summary['total_input_power']:.3f}W")
    print(f"  System eff: {summary['system_efficiency'] * 100:.1f}%")
    print("[PASS] test_system_summary")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("Power Tree Calculator Tests")
    print("=" * 50)
    all_pass = True
    for test in [test_simple_tree, test_buck_ldo_chain,
                 test_forward_voltage_propagation, test_system_summary]:
        try:
            if not test():
                all_pass = False
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            all_pass = False
        print()

    if all_pass:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")
        sys.exit(1)
