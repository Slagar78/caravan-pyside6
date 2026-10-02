@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ============================================
echo   Caravan build script
echo ============================================
echo.

echo [1/3] Cleaning old build...
if exist build (
    echo     Removing build\ ...
    rmdir /s /q build
)
if exist dist (
    echo     Removing dist\ ...
    rmdir /s /q dist
)
if exist Caravan.spec (
    echo     Removing Caravan.spec ...
    del /q Caravan.spec
)
echo     Done.
echo.

echo [2/3] Building Caravan.exe...
echo.

pyinstaller --onefile --windowed --clean --noconfirm ^
    --name "Caravan" ^
    --icon=ico/caravan.ico ^
    --add-data "caravan.cfg;." ^
    --add-data "68k.xml;." ^
    --add-data "alpha.png;." ^
    --add-data "ico;ico" ^
    --add-data "panels;panels" ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import shiboken6 ^
    --paths=panels ^
    --hidden-import splitter ^
    --hidden-import parsers ^
    caravan.py

if errorlevel 1 (
    echo.
    echo ============================================
    echo   BUILD FAILED!
    echo ============================================
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Build complete!
echo   Exe: dist\Caravan.exe
echo ============================================
echo.

pause