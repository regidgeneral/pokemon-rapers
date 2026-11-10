@echo off
setlocal
rem CAI LAN DAU tren mot may (vd may cong ty) - Duy 07/11.
rem Dat file nay vao thu muc game (cung cho voi file ROM .gba) roi bam dup. No se:
rem   1) noi git + lay code tool moi nhat (ghi de ban tool cu, GIU ROM/save; repo git cu thi cat sang nhanh truoc-dong-bo-lan-dau)
rem   2) lay save moi nhat ve (ban cu cua may nay cat vao save_backup\ neu choi it hon)
rem   3) tai mGBA ban dev (tu nap script) vao %LOCALAPPDATA%\ClaudeRE\mGBA-dev\
rem   4) mo game bang Choi.bat
rem Lan sau: luon mo game bang Choi.bat. File nay chi dung chu khong dau + CRLF (cmd doc sai dong co dau).
set "URL=https://github.com/regidgeneral/pokemon-rapers.git"
if not "%~1"=="" set "URL=%~1"
cd /d "%~dp0"

where git >nul 2>nul || (echo LOI: may nay chua cai Git ^(https://git-scm.com^). & pause & exit /b 1)
where py >nul 2>nul || (echo LOI: may nay chua cai Python 3 ^(py^). & pause & exit /b 1)
if defined SKIP_PLAY goto bat_dau
tasklist /FI "IMAGENAME eq mGBA.exe" /NH | find /i "mGBA.exe" >nul && (echo Dang mo mGBA: dong mGBA truoc roi chay lai. & pause & exit /b 1)
:bat_dau

echo === 1/4 Lay code tool tu GitHub (lan dau se hien cua so dang nhap GitHub) ===
if not exist ".git" git init -q
git remote get-url origin >nul 2>nul && git remote set-url origin "%URL%" || git remote add origin "%URL%"
git fetch origin || (echo LOI: khong lay duoc tu GitHub ^(mang / dang nhap^). & pause & exit /b 1)
git rev-parse --verify HEAD >nul 2>nul && git branch truoc-dong-bo-lan-dau >nul 2>nul
git checkout -f -B master origin/master || (echo LOI: khong lay duoc code. & pause & exit /b 1)
git branch --set-upstream-to origin/master >nul

echo === 2/4 Lay save moi nhat ===
cd /d "%~dp0tool"
py -3 save_sync.py init "%URL%"
py -3 save_sync.py pull
cd /d "%~dp0"

echo === 3/4 mGBA ban dev (co san trong mgba cua repo; khong co thi tai) ===
if defined SKIP_MGBA goto mo
if exist "%~dp0mgba\mGBA.exe" goto mo
set "DEV=%LOCALAPPDATA%\ClaudeRE\mGBA-dev"
for /d %%D in ("%DEV%\mGBA-build-*") do if exist "%%D\mGBA.exe" goto mo
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop'; $c=Join-Path $env:LOCALAPPDATA 'ClaudeRE'; New-Item -ItemType Directory -Force (Join-Path $c '7zr'),(Join-Path $c 'mGBA-dev-download') | Out-Null;" ^
  "Invoke-WebRequest 'https://www.7-zip.org/a/7zr.exe' -OutFile (Join-Path $c '7zr\7zr.exe');" ^
  "Invoke-WebRequest 'https://s3.amazonaws.com/mgba/mGBA-build-latest-win64.7z' -OutFile (Join-Path $c 'mGBA-dev-download\mGBA-build-latest-win64.7z');" ^
  "& (Join-Path $c '7zr\7zr.exe') x -y ('-o' + (Join-Path $c 'mGBA-dev')) (Join-Path $c 'mGBA-dev-download\mGBA-build-latest-win64.7z') | Out-Null;" ^
  "Get-ChildItem (Join-Path $c 'mGBA-dev') -Directory | ForEach-Object { New-Item -ItemType File -Force (Join-Path $_.FullName 'portable.ini') | Out-Null }"
if errorlevel 1 echo Khong tai duoc mGBA dev: Choi.bat se dung mGBA ban thuong ^(nap script tay^).

:mo
echo === 4/4 Mo game ===
if defined SKIP_PLAY exit /b 0
call "%~dp0Choi.bat"
