import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "pygame"],
    capture_output=True,
    text=True,
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)
