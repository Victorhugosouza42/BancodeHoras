@echo off
title Configurador do Sistema de Gestao de Folgas
cls

echo ======================================================
echo  Configurador Automatico do Sistema de Gestao de Folgas
echo ======================================================
echo.

REM Passo 1: Verificar se o Python esta instalado e no PATH.
echo Verificando a instalacao do Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERRO: Python nao encontrado no PATH.
    echo Por favor, instale o Python a partir de python.org
    echo e certifique-se de que marca a opcao "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b
)
echo Python encontrado!

REM Passo 2: Instalar a dependencia Flask.
echo.
echo Instalando a dependencia Flask (pode demorar um pouco)...
pip install Flask >nul
echo Flask instalado com sucesso!

REM Passo 3: Criar o banco de dados (se nao existir).
echo.
if exist database.db (
    echo O banco de dados 'database.db' ja existe. A pular a criacao.
) else (
    echo Criando o banco de dados e o utilizador admin...
    python -c "from app import init_db; init_db()"
)

REM Passo 4: Iniciar a aplicacao.
echo.
echo ======================================================
echo  Tudo pronto! A iniciar o servidor Flask...
echo  Abra o seu navegador em http://127.0.0.1:5000
echo  Pressione Ctrl+C nesta janela para parar o servidor.
echo ======================================================
echo.
flask run

echo.
pause