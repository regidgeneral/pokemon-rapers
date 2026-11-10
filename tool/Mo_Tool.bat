@echo off
cd /d "%~dp0"
py -3 mm_gui.py
if errorlevel 1 pause
