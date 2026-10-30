@echo off
setlocal
cd /d "%~dp0"

set "BROWSER=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist "%BROWSER%" set "BROWSER=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not exist "%BROWSER%" set "BROWSER=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not exist "%BROWSER%" set "BROWSER=C:\Program Files\Microsoft\Edge\Application\msedge.exe"

"%BROWSER%" --headless=new --disable-gpu --no-pdf-header-footer --print-to-pdf="%~dp0Projeto_Inicial_SMA_Walker_Guardiao.pdf" "file:///%~dp0relatorio_pi.html"

if exist "%~dp0Projeto_Inicial_SMA_Walker_Guardiao.pdf" (
    echo [OK] PDF gerado com sucesso: %~dp0Projeto_Inicial_SMA_Walker_Guardiao.pdf
) else (
    echo [ERRO] Nao foi possivel gerar o PDF. Verifique se o Chrome ou Edge estao instalados.
)
pause
