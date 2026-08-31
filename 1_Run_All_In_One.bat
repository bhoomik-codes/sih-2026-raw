@echo off
echo ===========================================
echo   IBVAP: ALL-IN-ONE LAPTOP DEPLOYMENT
echo ===========================================
echo Starting Command Center Backend...
start "IBVAP Backend" cmd /k ".\.venv\Scripts\activate && uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting Command Center Dashboard...
start "IBVAP Dashboard" cmd /k "cd apps\dashboard && npm run dev -- --host"

echo Starting Local Edge AI Node...
set /p CAMERA_IP="Enter your Camera URL (or press Enter for test video): "
if "%CAMERA_IP%"=="" set CAMERA_IP=data/videos/test_video.mp4

rem Ensure transmitter points to localhost
.\.venv\Scripts\python -c "import yaml; c=yaml.safe_load(open('configs/phase1_default.yaml')); c.setdefault('transmitter',{})['backend_ws_url']='ws://localhost:8000/ws'; yaml.safe_dump(c, open('configs/phase1_default.yaml', 'w'))"

start "IBVAP Edge Node" cmd /k ".\.venv\Scripts\activate && python -m apps.edge.main --source \"%CAMERA_IP%\""

echo.
echo All components started! Dashboard available at http://localhost:5173
pause
