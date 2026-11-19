from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PROJECTS = (
    "01-stategraph-agent",
    "02-agent-handoff-runtime",
    "03-browser-research-agent",
    "04-safe-coding-agent",
)

def main() -> int:
    temp_dir = ROOT / ".verify-temp"
    if temp_dir.exists():
        existing = tuple(temp_dir.iterdir())
        if existing:
            print(f"Refusing to delete pre-existing, non-empty test temp directory: {temp_dir}")
            return 2
    else:
        temp_dir.mkdir()
    env = os.environ.copy()
    env.update({"PYTHONUTF8": "1", "TEMP": str(temp_dir), "TMP": str(temp_dir)})
    summary = []
    try:
        for name in PROJECTS:
            project = ROOT / name
            if not project.is_dir():
                summary.append({"project": name, "result": "missing project"})
                continue
            readme = project / "README.md"
            dependencies = project / "requirements.txt"
            if not readme.is_file() or not dependencies.is_file():
                summary.append({"project": name, "result": "missing README.md or requirements.txt"})
                continue
            print(f"\n{'=' * 72}\n{name}: unit tests\n{'=' * 72}", flush=True)
            tests = subprocess.run(
                [sys.executable, "-X", "utf8", "-m", "unittest", "discover", "-s", "tests", "-v"],
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
            )
            print(tests.stdout, end="")
            print(tests.stderr, end="", file=sys.stderr)
            match = re.search(r"Ran (\d+) tests? in", tests.stderr + tests.stdout)
            test_count = int(match.group(1)) if match else 0
            tests_ok = tests.returncode == 0 and test_count >= 8 and re.search(
                r"\nOK(?: \([^\n]*\))?\s*$", tests.stderr + tests.stdout
            ) is not None
            print(f"\n{'=' * 72}\n{name}: offline demo\n{'=' * 72}", flush=True)
            demo = subprocess.run(
                [sys.executable, "-X", "utf8", "demo.py"],
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
            if demo.stdout:
                print(demo.stdout)
            if demo.stderr:
                print(demo.stderr, file=sys.stderr)
            demo_ok = demo.returncode == 0 and bool(demo.stdout.strip())
            status = "PASS" if tests_ok and demo_ok else "FAIL"
            summary.append({"project": name, "tests": test_count, "tests_ok": tests_ok, "demo_ok": demo_ok, "result": status})
            print(f"{name}: {status} ({test_count} tests; demo exit {demo.returncode})", flush=True)
        print("\nVerification summary")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if len(summary) == len(PROJECTS) and all(item.get("result") == "PASS" for item in summary) else 1
    except subprocess.TimeoutExpired as exc:
        print(f"Verification timeout (no network was requested): {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            next(temp_dir.iterdir())
        except StopIteration:
            temp_dir.rmdir()
        except OSError as exc:
            print(f"Retaining non-empty verification directory rather than deleting contents: {exc}", file=sys.stderr)

if __name__ == "__main__":
    raise SystemExit(main())
