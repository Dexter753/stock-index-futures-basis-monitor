@echo off
echo 正在打包股指期货基差监控系统...
cd /d "e:\stock-index-futures-basis-monitor"
pyinstaller ^
    -F ^
    -w ^
    --name="股指期货基差监控" ^
    --add-data="README.md;." ^
    --hidden-import=paramiko ^
    --hidden-import=pandas ^
    --hidden-import=openpyxl ^
    --hidden-import=pyautogui ^
    --hidden-import=PyQt5 ^
    basis_monitor_pyqt.py
echo 打包完成！
pause