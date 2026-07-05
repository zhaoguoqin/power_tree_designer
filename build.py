"""PyInstaller 打包脚本

使用方法:
    .venv\Scripts\python.exe build.py

输出:
    dist\电源树设计器.exe  (单个 exe 文件，可直接双击运行)
"""

import sys
import shutil
from pathlib import Path


def main():
    base_dir = Path(__file__).resolve().parent

    modules_dir = base_dir / "modules"
    modules_dir.mkdir(exist_ok=True)

    sep = ";" if sys.platform == "win32" else ":"

    args = [
        str(base_dir / "src" / "main.py"),
        "--name=电源树设计器",
        "--onefile",                     # 单文件 exe
        "--windowed",                    # 无控制台窗口
        f"--add-data={modules_dir}{sep}modules",
        "--clean",
        "--noconfirm",
        "--distpath", str(base_dir / "dist"),
        "--workpath", str(base_dir / "build_temp"),
        "--specpath", str(base_dir),
    ]

    icon_path = base_dir / "resources" / "icons" / "app.ico"
    if icon_path.exists():
        args.append(f"--icon={icon_path}")

    import PyInstaller.__main__
    PyInstaller.__main__.run(args)

    # 清理 spec 文件
    spec_file = base_dir / "电源树设计器.spec"
    if spec_file.exists():
        spec_file.unlink()

    exe_path = base_dir / "dist" / "电源树设计器.exe"
    if exe_path.exists():
        # 显示文件大小
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 50)
        print("  Build successful!")
        print(f"  Output: {exe_path}")
        print(f"  Size: {size_mb:.1f} MB")
        print("=" * 50)
        print("\n  Double-click to run. No Python installation needed.")
    else:
        print("\n  Build may have failed. Check messages above.")


if __name__ == "__main__":
    main()
