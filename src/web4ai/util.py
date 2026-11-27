from os import getenv
import subprocess
from pathlib import Path


def rg(src: str, pattern: str):
    result = subprocess.run(["rg", "-n", "-m", "500", pattern], input=src, text=True, capture_output=True, check=False)
    match result.returncode:
        case 2:
            return result.stderr
        case 1:
            return "No matches found."
        case 0:
            return result.stdout
    return "Unknown state."

def get_project_root() -> Path:
    root_env = getenv("PROJECT_ROOT")
    return Path(root_env) if root_env else Path(__file__).parent.parent.parent
