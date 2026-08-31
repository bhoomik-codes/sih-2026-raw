@echo off
echo ===========================================
echo       IBVAP: EDGE AI NODE DEPLOYMENT
echo ===========================================
echo.
set /p CC_IP="Enter the IPv4 Address of the Command Center Laptop (e.g. 192.168.1.100): "
if "%CC_IP%"=="" (
    echo Command Center IP is required.
    pause
    exit /b
)

set /p CAMERA_IP="Enter your Camera URL (or press Enter for test video): "
if "%CAMERA_IP%"=="" set CAMERA_IP=data/videos/test_video.mp4

echo.
echo Configuring Edge Node to transmit to ws://%CC_IP%:8000/ws...
.\.venv\Scripts\python -c "import yaml; c=yaml.safe_load(open('configs/phase1_default.yaml')); c.setdefault('transmitter',{})['backend_ws_url']='ws://%CC_IP%:8000/ws'; yaml.safe_dump(c, open('configs/phase1_default.yaml', 'w'))"

echo Starting Edge Node...
.\.venv\Scripts\activate && python -m apps.edge.main --source "%CAMERA_IP%"
pause
