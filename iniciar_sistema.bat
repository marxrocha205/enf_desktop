@echo off
title Sistema Farmaceutico & Dispensacao IoT (OLED Arduino)
chcp 65001 >nul

echo ==============================================================
echo   INICIANDO SISTEMA FARMACÊUTICO & DISPENSAÇÃO DESKTOP
echo ==============================================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app_desktop.py
) else (
    python app_desktop.py
)

if %errorlevel% neq 0 (
    echo.
    echo Ocorreu um erro ao iniciar a aplicação.
    pause
)
