"""Command line.

uv run python -m harness list
uv run python -m harness check --week 5 --in-process
uv run python -m harness check --week 5 --url https://<your-app>.azurecontainerapps.io
"""

import argparse
import os
import sys
from pathlib import Path

from harness import __version__
from harness.client import Target
from harness.engine import run_week
from harness.report import save, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harness", description="Check a Lakeshore Ride endpoint.")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Run the checks for one week.")
    check.add_argument("--week", type=int, required=True, choices=[5, 6, 7, 8, 10])
    where = check.add_mutually_exclusive_group(required=True)
    where.add_argument("--url", help="Base URL of the service, e.g. http://localhost:8000")
    where.add_argument("--in-process", action="store_true", help="Run app.main inside this process (no server needed).")
    check.add_argument(
        "--api-key",
        default=os.environ.get("SERVICE_API_KEY") or None,
        help="Value for the X-API-Key header (Week 10). Defaults to $SERVICE_API_KEY.",
    )
    check.add_argument("--pack", type=Path, help="Folder with extra data or checks (instructors).")
    check.add_argument("--out", type=Path, default=Path("reports"), help="Where to write the report.")
    check.add_argument("--timeout", type=float, default=90.0, help="Seconds per request.")

    sub.add_parser("list", help="List the checks for every week.")
    args = parser.parse_args(argv)

    if args.command == "list":
        from harness.checks import CORE, WEEKS

        for week, checks in WEEKS.items():
            print(f"Week {week}")
            for c in [*CORE, *checks]:
                print(f"  {c.id:24s} weight {c.weight:g}  {c.title}")
        return 0

    if args.url and not args.url.startswith(("http://", "https://")):
        parser.error("--url must start with http:// or https://")

    print(f"Lakeshore Ride harness {__version__}: week {args.week}")
    if args.in_process:
        from fastapi.testclient import TestClient

        from app.main import create_app

        with TestClient(create_app(), raise_server_exceptions=False) as client:
            report = run_week(args.week, Target(client=client, api_key=args.api_key), args.pack, _progress)
    else:
        target = Target(args.url, api_key=args.api_key, timeout=args.timeout)
        print(f"Target: {args.url} (the first call can take ~20 s if the app scaled to zero)")
        report = run_week(args.week, target, args.pack, _progress)

    print("\r" + " " * 60 + "\r", end="")
    print(summary(report))
    json_path, md_path = save(report, args.out)
    print(f"\nReport: {md_path}\nProof:  {json_path}")
    return 0 if report.results[0].score > 0 else 2


def _progress(check_id: str) -> None:
    print(f"\r  running {check_id:<40}", end="", flush=True)


if __name__ == "__main__":
    sys.exit(main())
