@echo off
rem Mo game co dong bo (Duy chot 07/11): lay code + save moi nhat tu GitHub -> mo mGBA -> dong mGBA thi day save len.
rem Co mGBA ban dev (0.11, co --script) trong %LOCALAPPDATA%\ClaudeRE\mGBA-dev\ thi dung no: tu nap mm_bridge.lua
rem (script tu mo tool). Khong co thi dung mGBA da cai, phai nap script tay (Tools > Scripting > File > Load script).
rem File nay chi dung chu khong dau + xuong dong CRLF: cmd doc sai dong co dau tieng Viet.
cd /d "%~dp0tool"
echo === Lay ban tool + save moi nhat ===
py -3 save_sync.py start
if errorlevel 1 (
  echo.
  echo Dong bo loi ^(xem dong LOI o tren^). Van mo game voi save dang co tren may nay.
  pause
)
set "ROM=%~dp0Pokemon - Emerald Version (USA, Europe).gba"
if not exist "%~dp0tool\sprites\fr\1.png" echo === Tao anh Pokemon lan dau ===
if not exist "%~dp0tool\sprites\fr\1.png" py -3 gen_sprites.py
set "MGBA="
for /d %%D in ("%LOCALAPPDATA%\ClaudeRE\mGBA-dev\mGBA-build-*") do if exist "%%D\mGBA.exe" set "MGBA=%%D\mGBA.exe"
rem Uu tien mGBA dev di kem repo (thu muc mgba\ canh ROM): may nao lay code ve cung co, chay y nhu may nha.
if not exist "%~dp0mgba\mGBA.exe" goto chon_xong
if not exist "%~dp0mgba\config.ini" copy /y "%~dp0mgba\config.ini.mau" "%~dp0mgba\config.ini" >nul
set "MGBA=%~dp0mgba\mGBA.exe"
:chon_xong
echo === Dang choi... dong mGBA xong se tu day save len ===
if not defined MGBA goto thuong
echo mGBA ban dev: tu nap script, tool tu mo.
start "" /wait "%MGBA%" --script "%~dp0tool\mm_bridge.lua" "%ROM%"
goto xong
:thuong
set "MGBA=C:\Program Files\mGBA\mGBA.exe"
if not exist "%MGBA%" set "MGBA=mGBA.exe"
echo mGBA ban thuong: nho nap mm_bridge.lua trong Tools ^> Scripting.
start "" /wait "%MGBA%" "%ROM%"
:xong
py -3 save_sync.py push
timeout /t 5
