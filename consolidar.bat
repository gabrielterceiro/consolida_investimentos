@echo off
SET "CURRENT_DIR=%~dp0"
docker run --rm -v "%CURRENT_DIR%input:/app/input" -v "%CURRENT_DIR%input/correcoes:/app/correcoes" -v "%CURRENT_DIR%output:/app/output" -v "%CURRENT_DIR%input/config:/app/config" consolidador-investimentos
pause