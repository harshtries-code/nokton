@echo off
echo Installing Nokton dependencies...
echo.

echo [1/3] Installing Python backend dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install Python dependencies.
    pause
    exit /b %errorlevel%
)
echo Done.
echo.

echo [2/3] Installing frontend dependencies...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo Failed to install frontend dependencies.
    pause
    exit /b %errorlevel%
)
cd ..
echo Done.
echo.

echo [3/3] Creating config directory...
if not exist "%USERPROFILE%\.nokton" mkdir "%USERPROFILE%\.nokton"
if not exist "%USERPROFILE%\.nokton\conversations" mkdir "%USERPROFILE%\.nokton\conversations"
if not exist "%USERPROFILE%\.nokton\logs" mkdir "%USERPROFILE%\.nokton\logs"
if not exist "%USERPROFILE%\.nokton\cache" mkdir "%USERPROFILE%\.nokton\cache"
echo Done.
echo.

echo Nokton installation complete!
echo Run scripts/run.bat to start Nokton.
pause
