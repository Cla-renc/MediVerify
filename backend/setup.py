"""
MediVerify — One-shot setup script.
Run this from c:\PROJECTS\MEDIVERIFY\backend\ :
    python setup.py
"""
import subprocess, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))

def run(cmd):
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=BASE)
    if result.returncode != 0:
        print(f"ERROR: command failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    print("OK")

python = sys.executable

run([python, "manage.py", "makemigrations", "authentication"])
run([python, "manage.py", "makemigrations", "products"])
run([python, "manage.py", "makemigrations", "reports"])
run([python, "manage.py", "makemigrations", "inventory"])
run([python, "manage.py", "makemigrations", "verification"])
run([python, "manage.py", "makemigrations", "gateway"])
run([python, "manage.py", "migrate"])
run([python, "manage.py", "seed_data"])

print("\n\n✅ Setup complete! Now run:  python manage.py runserver")
