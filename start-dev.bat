@echo off
setlocal enabledelayedexpansion

echo === 启动 BatchPrint 开发环境 ===
echo.

echo 启动后端服务 (uvicorn)...
start "BatchPrint Backend" cmd /k "cd /d %~dp0backend && uvicorn main:app --reload"

timeout /t 3 /nobreak

echo 启动前端服务 (Tauri)...
start "BatchPrint Frontend" cmd /k "cd /d %~dp0frontend && npx tauri dev"

echo.
echo 前端和后端正在启动...
echo 后端 API: http://localhost:8000 (文档: http://localhost:8000/docs)
echo 前端: 在 Tauri 窗口中运行
