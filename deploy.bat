@echo off
echo ==========================================
echo Railway Deployment Fix - Windows
echo ==========================================
echo.

echo Step 1: Stop any running monitors
taskkill /F /IM bash.exe /FI "WINDOWTITLE eq monitor*" 2>NUL
timeout /t 2 /nobreak >NUL

echo.
echo Step 2: Deploy to Railway
railway up --detach

echo.
echo Step 3: Wait for deployment (20 seconds)
timeout /t 20 /nobreak

echo.
echo Step 4: Check logs
railway logs --tail 30

echo.
echo Step 5: Test endpoint
timeout /t 3 /nobreak >NUL
curl -s -w "\nHTTP_CODE: %%{http_code}\n" "https://skintracker-production.up.railway.app/health"

echo.
echo Step 6: Check Railway status
railway status

echo.
echo ==========================================
echo Deployment process complete!
echo ==========================================
echo.
echo If still showing 502, try:
echo 1. Check Railway dashboard for multiple deployments
echo 2. Delete old deployments
echo 3. Wait 2-3 minutes for edge network to update
echo.
pause
