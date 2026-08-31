@echo off
echo ===========================================
echo     IBVAP: COMMAND CENTER DEPLOYMENT
echo ===========================================
echo Starting Command Center Backend...
start "IBVAP Backend" cmd /k ".\.venv\Scripts\activate && uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting Command Center Dashboard...
start "IBVAP Dashboard" cmd /k "cd apps\dashboard && npm run dev -- --host"

echo.
echo Command Center started! Other laptops can now connect their Edge Nodes to this machine.
echo Access the dashboard locally at http://localhost:5173
pause
