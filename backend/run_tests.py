"""Helper script: runs pytest and writes results summary to a text file."""
import subprocess, sys, pathlib

result = subprocess.run(
    [sys.executable, "-m", "pytest",
     "tests/test_backend.py", "tests/test_phase5_7.py",
     "-v", "--tb=short", "--no-header"],
    capture_output=True, text=True,
    cwd=pathlib.Path(__file__).parent
)

out = result.stdout + result.stderr
pathlib.Path("pytest_results.txt").write_text(out, encoding="utf-8")
print(out[-3000:] if len(out) > 3000 else out)
sys.exit(result.returncode)
