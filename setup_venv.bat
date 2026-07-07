@echo off
REM One-time setup for Windows (pip flavor). Needs Python 3.10+ (ADK requirement).
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
echo Creating .venv...
%PY% -m venv .venv
call .venv\Scripts\activate
pip install --quiet --upgrade pip
echo Installing dependencies...
pip install --quiet -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo Done. Next:
echo   1) put your GOOGLE_API_KEY in .env
echo   2) .venv\Scripts\activate
echo   3) cd 01_baseline ^&^& python driver.py Alice
