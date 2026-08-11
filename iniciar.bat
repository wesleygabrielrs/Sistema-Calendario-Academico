@echo off
chcp 65001 >nul
title Calendario Academico UNINASSAU
cd /d "%~dp0"
echo ============================================
echo   Subindo o Calendario Academico UNINASSAU
echo   Nao feche esta janela enquanto usar o app
echo   URL: http://127.0.0.1:5000/
echo ============================================
echo.

REM Abre o navegador com pequena pausa p/ o Flask subir
start "" cmd /c "timeout /t 3 /nobreak >nul & start "" http://127.0.0.1:5000/"

python run.py

echo.
echo Servidor encerrado. Pressione qualquer tecla para fechar.
pause >nul
