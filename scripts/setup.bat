@echo off
REM Windows setup: creates venv, installs backend + frontend dependencies.
cd /d %~dp0..
if not exist backend\.venv (
  python -m venv backend\.venv
)
call backend\.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
if not exist backend\.env copy backend\.env.example backend\.env
cd frontend
call npm install
cd ..
echo.
echo Setup complete. Next: install Ollama (https://ollama.com) and run: ollama pull qwen2.5:3b
echo Then run scripts\verify_models.py, scripts\run_backend.bat and scripts\run_frontend.bat
