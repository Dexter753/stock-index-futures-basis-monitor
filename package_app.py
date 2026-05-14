#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股指期货基差监控系统 - 打包脚本
"""

import subprocess
import sys
import os

def main():
    print("=" * 60)
    print("股指期货基差监控系统 - 打包脚本")
    print("=" * 60)
    
    # 检查 pyinstaller 是否安装
    try:
        import PyInstaller
        print("PyInstaller version:", PyInstaller.__version__)
    except ImportError:
        print("PyInstaller not installed, installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 打包命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "-F",                      # 打包为单个文件
        "-w",                      # 不显示控制台
        "--name=股指期货基差监控",     # 输出文件名
        "--hidden-import=paramiko",
        "--hidden-import=pandas",
        "--hidden-import=openpyxl",
        "--hidden-import=pyautogui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtPrintSupport",
        "basis_monitor_pyqt.py"
    ]
    
    print("\nRunning command:")
    print(" ".join(cmd))
    print("\n" + "=" * 60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd(), encoding='utf-8')
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        print("\n" + "=" * 60)
        if result.returncode == 0:
            print("Package success!")
            dist_path = os.path.join(os.getcwd(), "dist", "股指期货基差监控.exe")
            if os.path.exists(dist_path):
                print("Executable location:", dist_path)
                print("File size:", os.path.getsize(dist_path) / (1024 * 1024), "MB")
            else:
                print("Executable not found")
        else:
            print("Package failed, return code:", result.returncode)
            
    except Exception as e:
        print("Error during packaging:", str(e))

if __name__ == "__main__":
    main()