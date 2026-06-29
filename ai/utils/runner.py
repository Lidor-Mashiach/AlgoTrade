"""
Shared step runner.

Every folder runner (and the top-level pipeline runner) declares a list of steps as
(relative_script_path, description) tuples and hands it to run_steps. Each step runs in
its own subprocess, so the steps stay isolated and a failure stops the run. To skip a
step, comment out its tuple in the list.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys


def run_steps(base_dir: pathlib.Path, steps: list[tuple[str, str]]) -> None:
    """
    Run each step script in order, relative to base_dir. Raises if any step fails so the
    pipeline does not continue on a broken stage.
    """
    base_dir = pathlib.Path(base_dir)
    total = len(steps)
    for index, (relative_script, description) in enumerate(steps, start=1):
        script_path = base_dir / relative_script
        print("\n" + "=" * 78)
        print(f"[step {index}/{total}] {relative_script}")
        print(f"           {description}")
        print("=" * 78)

        if not script_path.exists():
            raise FileNotFoundError(f"Step script not found: {script_path}")

        subprocess.run([sys.executable, str(script_path)], check=True)

    print("\n" + "-" * 78)
    print(f"completed {total} step(s)")
    print("-" * 78)
