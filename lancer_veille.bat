@echo off
title Pipeline Veille BIM & IA
setlocal

:: Se placer dans le dossier contenant le script .bat
cd /d "%~dp0"

echo 🚀 1/2 : Recherche de nouveaux articles (main.py)...
:: Utilisation de guillemets pour securiser le chemin du fichier
uv run python "main.py"

echo.
echo ✅ Mise a jour terminee.
echo 🏗️ 2/2 : Lancement de l'interface de visualisation (app.py)...
echo (Le navigateur va s'ouvrir automatiquement)
echo.

:: Forcer l'execution via python pour eviter l'erreur de trampoline 'uv'
uv run python -m streamlit run "app.py"

pause