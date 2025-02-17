@echo off
setlocal enabledelayedexpansion

:main
cls
echo ============================
echo   Ollama Model Stop Script
echo ============================
echo.

echo Checking for running Ollama models...
ollama ps >nul 2>&1
set "psError=%ERRORLEVEL%"

if %psError% EQU 0 (
    echo ollama ps is available. Listing running models:
    echo.
    set index=0
    for /f "skip=1 tokens=1" %%A in ('ollama ps') do (
        set /a index+=1
        set "model[!index!]=%%A"
        echo !index!. %%A
    )
    if !index! EQU 0 (
        echo No running models found.
        pause
        exit /b
    )
) else (
    echo ollama ps command not available.
    echo Falling back to listing all models using ollama list:
    echo.
    set index=0
    for /f "skip=1 tokens=1" %%A in ('ollama list') do (
        set /a index+=1
        set "model[!index!]=%%A"
        echo !index!. %%A
    )
    if !index! EQU 0 (
        echo No models found.
        pause
        exit /b
    )
)

echo.
set /p choice="Enter the number of the model you want to stop (or press Enter to exit): "

if "%choice%"=="" (
    echo No selection made. Exiting.
    goto end
)

set /a choiceNum=%choice% 2>nul
if !choiceNum! LSS 1 (
    echo Invalid selection.
    pause
    goto main
)
if !choiceNum! GTR !index! (
    echo Invalid selection.
    pause
    goto main
)

call set "chosenModel=%%model[%choiceNum%]%%"
echo.
echo Stopping model: !chosenModel!
ollama stop !chosenModel!
if %ERRORLEVEL% EQU 0 (
    echo Model stopped successfully.
) else (
    echo Error stopping the model.
)
echo.
set /p again="Do you want to stop another model? (Y/N): "
if /I "!again!"=="Y" (
    goto main
) else (
    goto end
)

:end
echo.
pause
