@echo off
title HUST Course Advisor Server
echo ========================================================
echo   Dang khoi dong HUST Course Advisor Backend va Frontend
echo ========================================================

set "PATH=C:\Users\admin\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.20.0-win-x64;C:\Users\admin\AppData\Local\Programs\Python\Python312;%PATH%"
set "PYTHONPATH=E:\Vibe\et1_da1_hust\backend"

start "HUST-Backend" cmd /k "cd /d E:\Vibe\et1_da1_hust\backend && call .venv-win\Scripts\activate.bat && python run.py"

start "HUST-Frontend" cmd /k "cd /d E:\Vibe\et1_da1_hust\frontend && npm run dev"

ping 127.0.0.1 -n 3 >nul
start http://localhost:5173
echo Da khoi chay thanh cong tai http://localhost:5173
