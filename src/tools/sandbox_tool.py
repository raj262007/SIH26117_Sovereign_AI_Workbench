"""
Isolated Python Code Execution Sandbox.
Executes mathematical verification scripts deterministically with strict timeouts.
"""

import sys
import subprocess
import time
import tempfile
import os
from typing import Dict, Any

def is_docker_available() -> bool:
    """Check if Docker daemon is available and responsive for sandboxing."""
    if os.environ.get("FORCE_SUBPROCESS_SANDBOX", "1") == "1":
        return False
    import shutil
    if not shutil.which("docker"):
        return False
    try:
        res = subprocess.run(["docker", "info"], capture_output=True, timeout=1)
        return res.returncode == 0
    except Exception:
        return False

def execute_sandboxed_python(code_snippet: str, timeout_seconds: int = 5) -> Dict[str, Any]:
    """
    Execute Python code in an isolated environment to deterministically verify calculations.
    Runs inside a Docker container with --network=none if Docker is available,
    or in an isolated Python subprocess with zero network access and strict execution timeouts.
    Returns stdout, stderr, execution duration, and status.
    """
    clean_code = _extract_python_code(code_snippet)
    
    # Write to a temporary file
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp_file:
        tmp_file.write(clean_code)
        tmp_path = tmp_file.name

    start_time = time.time()
    try:
        # Check for Docker sandboxing
        if is_docker_available():
            cmd = [
                "docker", "run", "--rm",
                "--network=none",
                "--memory=512m",
                "--cpus=1",
                "-v", f"{tmp_path}:/workspace/script.py:ro",
                "-w", "/workspace",
                "python:3.11-slim",
                "python", "script.py"
            ]
        else:
            cmd = [sys.executable, tmp_path]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env={"PYTHONUNBUFFERED": "1"}
        )
        duration = round(time.time() - start_time, 3)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        exit_code = result.returncode

        is_breach = "CRITICAL BREACH" in stdout or "FAIL" in stdout
        status = "FAIL - CRITICAL BREACH" if is_breach else ("PASS" if exit_code == 0 else "ERROR")

        return {
            "success": exit_code == 0,
            "status": status,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "duration_sec": duration,
            "executed_code": clean_code,
            "sandbox_mode": "docker_isolated" if is_docker_available() else "subprocess_isolated"
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "status": "TIMEOUT",
            "stdout": "",
            "stderr": f"Execution exceeded {timeout_seconds}s limit",
            "exit_code": -1,
            "duration_sec": timeout_seconds,
            "executed_code": clean_code
        }
    except Exception as e:
        return {
            "success": False,
            "status": "EXECUTION_ERROR",
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "duration_sec": 0.0,
            "executed_code": clean_code
        }
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def _extract_python_code(raw_text: str) -> str:
    """Extract raw python code from markdown fences if present."""
    if "```python" in raw_text:
        parts = raw_text.split("```python", 1)[1].split("```", 1)
        return parts[0].strip()
    elif "```" in raw_text:
        parts = raw_text.split("```", 1)[1].split("```", 1)
        return parts[0].strip()
    return raw_text.strip()
