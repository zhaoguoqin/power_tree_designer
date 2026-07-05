# 电源树设计器 Power Tree Designer

一款用于电源树（Power Tree）设计、功率计算和可视化的桌面应用程序。

## 功能

- 🔌 **拖放式电源树拓扑图设计** — 从模块库拖动模块到画布，自动建立供电路径
- 📦 **自定义电源模块库** — 支持 Buck/Boost/LDO/输入电源/负载等类型，参数以 JSON 文件保存
- 📊 **实时功率计算** — 逐级计算电压、电流、功率、效率、损耗
- 💾 **项目文件管理** — 保存/打开 `.pwt` 项目文件
- 📋 **导出功能** — 导出计算结果 CSV 报表、树形图 PNG/SVG
- 🎨 **自动布局** — 树形图自动层级布局，支持缩放和平移

## 安装

### 从源码运行

```bash
# 克隆仓库
git clone <your-repo-url>
cd power-tree-designer

# 安装依赖
pip install -r requirements.txt

# 运行
python -m src.main
```

### 打包为 exe

```bash
pip install pyinstaller
python build.py
```

输出文件: `dist/电源树设计器.exe`

## 项目结构

```
power-tree-designer/
├── src/
│   ├── main.py                    # 入口
│   ├── models/
│   │   ├── power_module.py        # 电源模块数据模型
│   │   └── tree_node.py           # 树节点数据模型
│   ├── core/
│   │   ├── power_tree.py          # 电源树数据结构
│   │   ├── calculator.py          # 功率计算引擎
│   │   ├── module_manager.py      # 模块管理器
│   │   └── project_manager.py     # 项目管理器
│   └── ui/
│       ├── main_window.py         # 主窗口
│       ├── tree_canvas.py         # 画布组件
│       ├── tree_node_item.py      # 节点图形项
│       ├── tree_edge_item.py      # 连线图形项
│       ├── module_library.py      # 模块库面板
│       ├── property_panel.py      # 属性面板
│       └── dialogs/
│           ├── module_editor.py   # 模块编辑器
│           └── export_dialog.py   # 导出对话框
├── modules/                       # 预置模块库 (JSON)
├── resources/                     # 资源文件
├── tests/                         # 测试
├── requirements.txt
├── build.py                       # 打包脚本
└── README.md
```

## 使用指南

### 1. 创建电源树

1. 启动应用后，点击"新建项目"
2. 从左侧**模块库**中拖动一个"输入电源"到画布
3. 继续从模块库拖动 Buck/Boost/LDO 模块到画布，它们会自动连接到父节点
4. 最后拖动"负载"模块作为叶子节点

### 2. 编辑节点属性

1. 点击画布上的节点选中它
2. 在右侧**属性面板**中修改参数（输出电压、负载电流等）
3. 点击"应用"，计算结果会实时更新

### 3. 自定义模块

1. 在模块库面板点击"新建"
2. 填写模块参数（名称、类型、电压范围、效率等）
3. 保存后，模块会出现在库中并保存为 JSON 文件

### 4. 导出

1. 菜单栏: 文件 → 导出
2. 选择导出格式和路径
3. 支持 CSV 报表和 PNG/SVG 图形导出

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+N` | 新建项目 |
| `Ctrl+O` | 打开项目 |
| `Ctrl+S` | 保存 |
| `Ctrl+Shift+S` | 另存为 |
| `Ctrl+E` | 导出 |
| `Ctrl+L` | 自动布局 |
| `Ctrl+F` | 适应窗口 |
| `Ctrl+0` | 重置缩放 |
| `Delete` | 删除选中节点 |
| 滚轮 | 缩放 |
| 中键拖动 | 平移 |

## 技术栈

- **Python 3.10+**
- **PySide6** (Qt for Python)
- **PyInstaller** (打包)

## 开源许可

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
