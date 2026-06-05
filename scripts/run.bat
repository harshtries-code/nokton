@echo off
title Nokton
echo Starting Nokton...
echo.

echo [1/2] Starting Python backend...
start /B python -m backend.main

echo Waiting for backend to start...
timeout /t 3 /nobreak > nul
echo Done.
echo.

echo [2/2] Starting Electron frontend...
cd frontend
if "%1"=="--dev" (
    call npm run dev
) else (
    call npm start
)
cd ..

echo.
echo Nokton stopped.
pause
