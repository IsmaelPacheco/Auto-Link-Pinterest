@echo off
chcp 65001 > nul
title Recuperar Conta Pinterest - AutoLink
echo ========================================================
echo   AutoLink Pinterest - Abrindo Sessao para Recuperacao
echo ========================================================
echo.
.venv\Scripts\python.exe abrir_navegador_recuperacao.py
pause
