import subprocess


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
