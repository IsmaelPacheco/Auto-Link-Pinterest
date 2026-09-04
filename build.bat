@echo off
title Compilador Nexus Automator Pro (Portable - PyInstaller)
color 0A

echo ===================================================
echo   INICIANDO A COMPILACAO MODO PORTABLE (PYINSTALLER)
echo ===================================================
echo.

:: Limpa builds antigos para evitar conflitos
if exist "build" rmdir /s /q "build"
if exist "NexusAutomator_Portable" rmdir /s /q "NexusAutomator_Portable"

:: Compilacao com PyInstaller
:: --distpath cria diretamente na raiz
.venv\Scripts\pyinstaller.exe ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --name="NexusAutomator" ^
    --distpath="NexusAutomator_Portable" ^
    --icon="assets/icon.ico" ^
    --add-data "src/views/styles;src/views/styles" ^
    --add-data "assets;assets" ^
    --collect-all faster_whisper ^
    --collect-all av ^
    --collect-all moviepy ^
    --collect-all imageio ^
    --collect-all edge_tts ^
    --collect-all rembg ^
    --collect-all onnxruntime ^
    --collect-all feedparser ^
    --collect-all googleapiclient ^
    --collect-all mediapipe ^
    --copy-metadata pymatting ^
    main.py

echo.
echo ===================================================
echo   FINALIZANDO COMPILACAO
echo ===================================================
echo.

if exist "build" rmdir /s /q "build"
if exist "NexusAutomator.spec" del "NexusAutomator.spec"
if exist "main.spec" del "main.spec"

echo COMPILACAO CONCLUIDA COM SUCESSO!
echo A sua pasta "NexusAutomator_Portable\NexusAutomator" esta pronta!
echo Copie ela para qualquer PC e execute o NexusAutomator.exe.
echo.
pause
