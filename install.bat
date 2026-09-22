@echo off
python "%~dp0src\install.py" || goto :error
python "%LOCALAPPDATA%\Programs\FolderColors\foldercolor.py" preset "%LOCALAPPDATA%\Programs\FolderColors\presets\default.json" || goto :error
pause
exit /b 0

:error
echo Something went wrong.
pause
exit /b 1
