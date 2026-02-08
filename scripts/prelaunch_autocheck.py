#!/usr/bin/env python
"""
Automated pre-launch checks for items that can be validated from code/runtime.

Run:
    python scripts/prelaunch_autocheck.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PRODUCTION_PATH = ROOT_DIR / ".env.production"


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def run_command(name: str, args: list[str], env: dict[str, str] | None = None) -> StepResult:
    command_env = os.environ.copy()
    if env:
        command_env.update(env)

    completed = subprocess.run(
        args,
        cwd=ROOT_DIR,
        env=command_env,
        text=True,
        capture_output=True,
    )
    output = (completed.stdout + "\n" + completed.stderr).strip()
    last_line = output.splitlines()[-1] if output else "No output"
    return StepResult(name=name, ok=completed.returncode == 0, detail=last_line)


def validate_env_values(env_values: dict[str, str]) -> list[StepResult]:
    results: list[StepResult] = []

    if not env_values:
        results.append(
            StepResult(
                name="Env file `.env.production` ditemukan",
                ok=False,
                detail="File tidak ditemukan.",
            )
        )
        return results

    hosts_raw = env_values.get("DJANGO_ALLOWED_HOSTS", "")
    hosts = [host.strip().lower() for host in hosts_raw.split(",") if host.strip()]
    placeholder_hosts = {
        "yourdomain.com",
        "www.yourdomain.com",
        "api.yourdomain.com",
        "example.com",
        "localhost",
        "127.0.0.1",
        "::1",
        "testserver",
    }
    invalid_hosts = [host for host in hosts if host in placeholder_hosts]
    results.append(
        StepResult(
            name="Allowed hosts production final",
            ok=bool(hosts) and not invalid_hosts,
            detail=(
                "OK"
                if bool(hosts) and not invalid_hosts
                else f"Masih placeholder/dev host: {', '.join(invalid_hosts) or '(kosong)'}"
            ),
        )
    )

    origins_raw = env_values.get("DJANGO_CSRF_TRUSTED_ORIGINS", "")
    origins = [origin.strip() for origin in origins_raw.split(",") if origin.strip()]
    invalid_origins = [origin for origin in origins if not origin.lower().startswith("https://")]
    placeholder_origins = [origin for origin in origins if "yourdomain.com" in origin.lower() or "example.com" in origin.lower()]
    results.append(
        StepResult(
            name="CSRF trusted origins production final",
            ok=bool(origins) and not invalid_origins and not placeholder_origins,
            detail=(
                "OK"
                if bool(origins) and not invalid_origins and not placeholder_origins
                else f"Origins belum final/valid HTTPS: {', '.join(invalid_origins + placeholder_origins) or '(kosong)'}"
            ),
        )
    )

    midtrans_server = env_values.get("MIDTRANS_SERVER_KEY", "").strip()
    midtrans_client = env_values.get("MIDTRANS_CLIENT_KEY", "").strip()
    if midtrans_server and midtrans_client:
        results.append(StepResult(name="Midtrans keys (jika payment aktif)", ok=True, detail="Terisi."))
    else:
        results.append(
            StepResult(
                name="Midtrans keys (jika payment aktif)",
                ok=True,
                detail="Kosong. Aman jika payment belum diaktifkan saat launch.",
            )
        )

    return results


def main() -> int:
    env_values = parse_env_file(ENV_PRODUCTION_PATH)
    results = validate_env_values(env_values)

    py = sys.executable
    production_check_env = {
        "DJANGO_ENV": "production",
        # Force non-placeholder values so production settings validation can run
        # even when local .env still uses dev hosts.
        "DJANGO_ALLOWED_HOSTS": "launch-gate.internal",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "https://launch-gate.internal",
    }
    checks = [
        run_command(
            "Django check (production settings)",
            [py, "manage.py", "check", "--settings=config.settings.production"],
            env=production_check_env,
        ),
        run_command(
            "DB connectivity (production settings)",
            [
                py,
                "manage.py",
                "shell",
                "--settings=config.settings.production",
                "-c",
                "from django.db import connection; connection.cursor().execute('SELECT 1'); print('DB OK')",
            ],
            env=production_check_env,
        ),
        run_command(
            "Migrations up-to-date (production settings)",
            [py, "manage.py", "migrate", "--settings=config.settings.production", "--check"],
            env=production_check_env,
        ),
        run_command(
            "Security regression tests",
            [
                py,
                "manage.py",
                "test",
                "detail_project.tests_page_security_audit",
                "detail_project.tests_api_v2_access",
                "detail_project.tests_export_csrf",
                "detail_project.tests_export_access",
                "referensi.tests.test_audit_template_security",
                "referensi.tests.test_import_permissions",
                "--keepdb",
                "--noinput",
            ],
        ),
        run_command(
            "Functional smoke tests",
            [py, "manage.py", "test", "dashboard.tests_prelaunch_smoke", "--keepdb", "--noinput"],
        ),
    ]
    results.extend(checks)

    print("\n=== PRE-LAUNCH AUTO CHECK RESULT ===")
    failures = 0
    for result in results:
        icon = "PASS" if result.ok else "FAIL"
        print(f"[{icon}] {result.name} -> {result.detail}")
        if not result.ok:
            failures += 1

    print("\n=== MANUAL ITEMS (TIDAK BISA DIAUTOMASI PENUH) ===")
    print("- Backup DB terbaru + catat timestamp.")
    print("- Restore drill staging minimal 1x.")
    print("- Restriksi network/firewall akses DB.")
    print("- Monitoring 24 jam pertama + rollback rehearsal operasional.")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
