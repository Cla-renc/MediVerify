@echo off
echo ============================================
echo   MediVerify Backend Setup Script
echo ============================================

set PYTHON=C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe

if not exist %PYTHON% (
    echo ERROR: Python not found at %PYTHON%
    echo Trying python from PATH...
    set PYTHON=python
)

echo.
echo [1/4] Installing Python dependencies...
%PYTHON% -m pip install -r backend\requirements.txt
if errorlevel 1 (
    echo WARN: Some packages may already be installed. Continuing...
)

echo.
echo [2/4] Running Django migrations...
%PYTHON% backend\manage.py makemigrations authentication products inventory verification reports gateway
%PYTHON% backend\manage.py migrate

echo.
echo [3/4] Creating superuser...
echo from django.contrib.auth import get_user_model; U=get_user_model(); U.objects.filter(username='admin').exists() or U.objects.create_superuser('admin','admin@mediverify.co.ke','admin123', role='REGULATOR') | %PYTHON% backend\manage.py shell

echo.
echo [4/4] Seeding database with sample data...
%PYTHON% backend\manage.py seed_data

echo.
echo ============================================
echo   Setup complete!
echo   Run: %PYTHON% backend\manage.py runserver
echo ============================================
