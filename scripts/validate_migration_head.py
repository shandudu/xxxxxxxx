"""Verify that the configured MySQL database is at the single Alembic head."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    candidates = [ROOT / '.venv' / 'Scripts' / 'fba.exe', ROOT / '.venv' / 'bin' / 'fba']
    executable = next((str(path) for path in candidates if path.exists()), shutil.which('fba'))
    if not executable:
        print('ERROR: fba executable not found')
        return 1

    current = subprocess.run([executable, 'alembic', 'current'], cwd=ROOT, capture_output=True, text=True, check=False)
    heads = subprocess.run([executable, 'alembic', 'heads'], cwd=ROOT, capture_output=True, text=True, check=False)
    if current.returncode != 0 or heads.returncode != 0:
        print(current.stdout + current.stderr + heads.stdout + heads.stderr)
        return 1

    head_lines = [line.split()[0] for line in heads.stdout.splitlines() if line.strip() and not line.startswith('INFO')]
    if len(head_lines) != 1 or head_lines[0] not in current.stdout:
        print(f'ERROR: migration mismatch current={current.stdout!r} heads={head_lines!r}')
        return 1
    print(f'OK: Alembic current=head ({head_lines[0]})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
