@echo off
cd /d E:\xtreegram-build\desktop
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-windows.ps1 -Configuration Release > E:\xtreegram-build\logs\build.log 2>&1
echo EXIT=%ERRORLEVEL% >> E:\xtreegram-build\logs\build.log
