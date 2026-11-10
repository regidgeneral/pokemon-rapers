@echo off
rem Choi thu KHONG dong bo (Duy 08/11: thu new game): khong lay save tu GitHub, khong day save len khi dong.
rem Tool van tu thu day save, nhung bi tu choi vi ban tren GitHub choi lau hon -> save cu tren GitHub an toan.
rem Muon quay ve save cu: bam Choi.bat nhu thuong (new game cat vao save_backup, khong mat).
set "ROM=%~dp02207 - Pokemon - Versione Smeraldo (I)(Pokemon Rapers).gba"
if not exist "%~dp0mgba\config.ini" copy /y "%~dp0mgba\config.ini.mau" "%~dp0mgba\config.ini" >nul
start "" "%~dp0mgba\mGBA.exe" --script "%~dp0tool\mm_bridge.lua" "%ROM%"
