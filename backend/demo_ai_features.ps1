$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

python manage.py migrate
python manage.py seed_data
python manage.py generate_synthetic_scans --seed 42 --genuine 60 --clones-per-type 15
python manage.py train_clone_model --seed 42
python manage.py evaluate_clone_detection
python manage.py evaluate_ocr
python manage.py evaluate_chatbot

Write-Output 'AI demo data and evaluations are ready. Open the frontend and verify a genuine code to try chat; use the pharmacist account to scan stock.'
