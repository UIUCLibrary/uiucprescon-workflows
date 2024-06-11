@echo off

set PYTHON_SCRIPT=%~dp0\..\packaging\package_speedwagon.py
set BUILD_VENV=build\build_standalone_build_env

goto :init

:create_venv
    py -m venv %BUILD_VENV%
    %BUILD_VENV%\Scripts\python -m pip install pip --upgrade
    %BUILD_VENV%\Scripts\python -m pip install PyInstaller cmake
    goto :eof

:create_standalone
    %BUILD_VENV%\Scripts\python %PYTHON_SCRIPT% %*
    goto :eof

:init
    echo %*
    call :create_venv
    call :create_standalone %*

