#!/usr/bin/env python3
"""
scripts/validate_submission.py
================================
Python-based pre-submission validator (cross-platform — works on Windows too).

Replicates the 3-step check from the PS bash validator:
  Step 1: Ping HF Space /reset endpoint → must return HTTP 200
  Step 2: docker build in repo root → must succeed
  Step 3: openenv validate → must pass

Usage:
    python scripts/validate_submission.py <ping_url> [repo_dir]

    ping_url - Your HuggingFace Space URL (e.g. https://your-space.hf.space)
    repo_dir - Path to your repo root (default: current directory)

Examples:
    python scripts/validate_submission.py https://my-team.hf.space
    python scripts/validate_submission.py https://my-team.hf.space ./

Exit codes:
    0 — All checks passed
    1 — One or more checks failed
"""

from __future__ import annotations

import os
import sys
import subprocess
import time
from pathlib import Path

# ── Optional: try httpx first, fall back to urllib ──────────────────────────
try:
    import httpx
    _USE_HTTPX = True
except ImportError:
    import urllib.request
    import urllib.error
    _USE_HTTPX = False


# ============================================================================
# Colour helpers
# ============================================================================

_IS_TTY = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    if not _IS_TTY:
        return text
    return f"\033[{code}m{text}\033[0m"

def green(t):  return _c("0;32", t)
def red(t):    return _c("0;31", t)
def yellow(t): return _c("1;33", t)
def bold(t):   return _c("1",    t)


# ============================================================================
# Logger helpers
# ============================================================================

PASS_COUNT = 0

def log(msg: str):
    ts = time.strftime("%H:%M:%S", time.gmtime())
    print(f"[{ts}] {msg}")

def passed(label: str):
    global PASS_COUNT
    PASS_COUNT += 1
    log(f"{green('PASSED')} -- {label}")

def failed(label: str):
    log(f"{red('FAILED')} -- {label}")

def hint(msg: str):
    print(f"  {yellow('Hint:')} {msg}")

def stop_at(step: str):
    print()
    print(f"{red(bold(f'Validation stopped at {step}.'))} Fix the above before continuing.")
    sys.exit(1)


# ============================================================================
# Step 1 — Ping HF Space
# ============================================================================

def step1_ping(ping_url: str) -> None:
    log(f"{bold('Step 1/3: Pinging HF Space')} ({ping_url}/reset) ...")
    reset_url = ping_url.rstrip("/") + "/reset"

    status_code = 0
    try:
        if _USE_HTTPX:
            resp = httpx.post(
                reset_url,
                json={},
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
            status_code = resp.status_code
        else:
            req = urllib.request.Request(
                reset_url,
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                status_code = r.status
    except Exception as exc:
        failed("HF Space not reachable")
        hint(f"Error: {exc}")
        hint(f"Try: curl -s -o /dev/null -w '%{{http_code}}' -X POST {reset_url}")
        stop_at("Step 1")

    if status_code == 200:
        passed("HF Space is live and responds to /reset")
    else:
        failed(f"HF Space /reset returned HTTP {status_code} (expected 200)")
        hint("Make sure your Space is running and the URL is correct.")
        hint(f"Try opening {ping_url} in your browser first.")
        stop_at("Step 1")


# ============================================================================
# Step 2 — Docker build
# ============================================================================

def step2_docker_build(repo_dir: Path) -> None:
    log(f"{bold('Step 2/3: Running docker build')} ...")

    # Find docker
    docker_cmd = "docker"
    result = subprocess.run([docker_cmd, "--version"], capture_output=True)
    if result.returncode != 0:
        failed("docker command not found")
        hint("Install Docker: https://docs.docker.com/get-docker/")
        stop_at("Step 2")

    # Find Dockerfile
    if (repo_dir / "Dockerfile").exists():
        context = repo_dir
    elif (repo_dir / "server" / "Dockerfile").exists():
        context = repo_dir / "server"
    else:
        failed("No Dockerfile found in repo root or server/ directory")
        stop_at("Step 2")

    log(f"  Found Dockerfile in {context}")

    build_result = subprocess.run(
        [docker_cmd, "build", str(context)],
        capture_output=True,
        text=True,
        timeout=600,
    )

    if build_result.returncode == 0:
        passed("Docker build succeeded")
    else:
        failed("Docker build failed")
        # Show last 20 lines of output
        output = (build_result.stdout + build_result.stderr).strip().splitlines()
        for line in output[-20:]:
            print(f"  {line}")
        stop_at("Step 2")


# ============================================================================
# Step 3 — openenv validate
# ============================================================================

def step3_openenv_validate(repo_dir: Path) -> None:
    log(f"{bold('Step 3/3: Running openenv validate')} ...")

    # Check if openenv is installed
    check = subprocess.run(
        [sys.executable, "-m", "openenv", "--version"],
        capture_output=True,
    )
    openenv_available = check.returncode == 0

    if not openenv_available:
        # Try as a direct command
        check2 = subprocess.run(["openenv", "--version"], capture_output=True)
        openenv_available = check2.returncode == 0
        openenv_cmd = ["openenv", "validate"]
    else:
        openenv_cmd = [sys.executable, "-m", "openenv", "validate"]

    if not openenv_available:
        failed("openenv command not found")
        hint("Install it: pip install openenv-core")
        stop_at("Step 3")

    validate_result = subprocess.run(
        openenv_cmd,
        capture_output=True,
        text=True,
        cwd=str(repo_dir),
    )

    if validate_result.returncode == 0:
        passed("openenv validate passed")
        out = (validate_result.stdout or "").strip()
        if out:
            log(f"  {out}")
    else:
        failed("openenv validate failed")
        print(validate_result.stdout)
        print(validate_result.stderr)
        stop_at("Step 3")


# ============================================================================
# Additional local checks (bonus — always run even without HF Space URL)
# ============================================================================

def step_local_checks(repo_dir: Path) -> None:
    """Run fast local sanity checks that don't need Docker or HF Space."""
    log(bold("Local checks (fast sanity) ..."))

    checks = [
        ("inference.py exists",     (repo_dir / "inference.py").exists()),
        ("openenv.yaml exists",     (repo_dir / "openenv.yaml").exists()),
        ("Dockerfile exists",       (repo_dir / "Dockerfile").exists()),
        ("requirements.txt exists", (repo_dir / "requirements.txt").exists()),
        ("env/models.py exists",    (repo_dir / "env" / "models.py").exists()),
        ("env/environment.py has get_state()", _file_contains(repo_dir / "env" / "environment.py", "def get_state")),
        ("inference.py has [START]",       _file_contains(repo_dir / "inference.py", "[START]")),
        ("inference.py has OpenAI client", _file_contains(repo_dir / "inference.py", "OpenAI(")),
        ("inference.py uses HF_TOKEN",     _file_contains(repo_dir / "inference.py", "HF_TOKEN")),
        ("inference.py has [STEP]",        _file_contains(repo_dir / "inference.py", "[STEP]")),
        ("inference.py has [END]",         _file_contains(repo_dir / "inference.py", "[END]")),
        ("openenv.yaml no Python docstring", not _file_starts_with_docstring(repo_dir / "openenv.yaml")),
        ("Dockerfile no Python docstring",   not _file_starts_with_docstring(repo_dir / "Dockerfile")),
    ]

    all_pass = True
    for label, ok in checks:
        if ok:
            log(f"  {green('OK')}  {label}")
        else:
            log(f"  {red('FAIL')} {label}")
            all_pass = False

    return all_pass


def _file_contains(path: Path, text: str) -> bool:
    try:
        return text in path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False


def _file_starts_with_docstring(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore").lstrip()
        return content.startswith('"""')
    except Exception:
        return False


# ============================================================================
# Main
# ============================================================================

def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    ping_url = args[0]
    repo_dir = Path(args[1]).resolve() if len(args) > 1 else Path.cwd()

    if not repo_dir.is_dir():
        print(f"Error: directory '{repo_dir}' not found")
        sys.exit(1)

    ping_url = ping_url.rstrip("/")

    print()
    print(bold("=" * 48))
    print(bold("  OpenEnv Submission Validator (Python)"))
    print(bold("=" * 48))
    log(f"Repo:     {repo_dir}")
    log(f"Ping URL: {ping_url}")
    print()

    # Always run local checks first (fast, no network/docker needed)
    local_ok = step_local_checks(repo_dir)
    print()

    # Network/infra checks
    step1_ping(ping_url)
    step2_docker_build(repo_dir)
    step3_openenv_validate(repo_dir)

    print()
    print(bold("=" * 48))
    if local_ok:
        print(f"{green(bold('  All checks passed! Submission ready.'))} ")
    else:
        print(f"{yellow(bold('  Infra checks passed but some local checks failed.'))} ")
    print(bold("=" * 48))
    print()


if __name__ == "__main__":
    main()
