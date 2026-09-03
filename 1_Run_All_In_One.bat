@echo off
echo ===========================================
echo   IBVAP: ALL-IN-ONE LAPTOP DEPLOYMENT
echo ===========================================
echo Starting Command Center Backend...
start "IBVAP Backend" cmd /k ".\.venv\Scripts\activate && uvicorn apps.backend.main:app --host 0.0.0.0 --port 8001 --reload"

echo Starting Command Center Dashboard...
start "IBVAP Dashboard" cmd /k "cd apps\dashboard && npm run dev -- --host"

echo The system is now running. Please use the Dashboard to add and start cameras!

echo.
echo All components started! Dashboard available at http://localhost:5173
pause
