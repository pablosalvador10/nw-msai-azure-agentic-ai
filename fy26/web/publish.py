"""Build the website image and roll it out. Run from fy26/ after `terraform apply` in web/infra:

    uv run python -m web.publish              # stage, build in ACR, apply, wait until live
    uv run python -m web.publish --stage-only # only write web/build/ (to inspect or docker build locally)

Every command it runs is printed first, like course.py: copy any of them into a terminal.
"""

import argparse
import io
import json
import shutil
import subprocess
import tarfile
import time
from datetime import datetime
from pathlib import Path

import httpx2

import course
from web.site import published_files

FY26 = course.FY26
WEB = FY26 / "web"
INFRA = WEB / "infra"
BUILD = WEB / "build"
RUNTIME = [
    "__init__.py",
    "auth.py",
    "catalog.py",
    "config.py",
    "hints.py",
    "main.py",
    "render.py",
    "runs.py",
    "shell.py",
    "site.py",
]


def committed() -> dict[str, bytes]:
    """fy26/ as of the last commit (HEAD): edits that are not committed yet never reach the site."""
    # Run from fy26/, git archive packs only this folder, with paths relative to it.
    print("$ git archive HEAD")
    tar = subprocess.run(["git", "archive", "HEAD"], cwd=FY26, capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(tar)) as archive:
        return {m.name: archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}


def stage() -> Path:
    """Copy exactly what the image needs into web/build/: nothing else reaches the registry."""
    shutil.rmtree(BUILD, ignore_errors=True)
    (BUILD / "web").mkdir(parents=True)
    shutil.copy2(WEB / "Dockerfile", BUILD / "Dockerfile")
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy2(FY26 / name, BUILD / name)
    shutil.copytree(FY26 / "harness", BUILD / "harness", ignore=shutil.ignore_patterns("__pycache__"))
    for name in RUNTIME:
        shutil.copy2(WEB / name, BUILD / "web" / name)
    shutil.copytree(WEB / "static", BUILD / "web" / "static", ignore=shutil.ignore_patterns("vendor"))
    files = committed()
    pages = [rel for rel in published_files(FY26) if rel in files]
    skipped = sorted(set(published_files(FY26)) - set(pages))
    for rel in pages:
        (BUILD / "site" / rel).parent.mkdir(parents=True, exist_ok=True)
        (BUILD / "site" / rel).write_bytes(files[rel])
    print(f"Staged {BUILD.relative_to(FY26)}/ with {len(pages)} course files.")
    if skipped:
        print(f"Not published (not committed yet): {', '.join(skipped)}")
    return BUILD


def outputs() -> dict:
    raw = json.loads(course.run(["terraform", f"-chdir={INFRA.relative_to(FY26)}", "output", "-json"], quiet=True))
    return {name: item["value"] for name, item in raw.items()}


def wait_until_live(url: str, version: str, timeout_s: int = 300) -> None:
    print(f"Waiting for {url} to serve version {version} ...", end="", flush=True)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            health = httpx2.get(f"{url}/healthz", timeout=30)
            if health.status_code == 200 and health.json().get("version") == version:
                print(" live.")
                return
        except (httpx2.HTTPError, ValueError):
            pass
        print(".", end="", flush=True)
        time.sleep(10)
    raise TimeoutError(f"{url} is not serving {version} yet: az containerapp revision list -n <app> -g <rg> -o table")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and deploy the course website.")
    parser.add_argument("--tag", help="Image tag (default: a timestamp).")
    parser.add_argument("--stage-only", action="store_true", help="Only stage web/build/.")
    args = parser.parse_args()

    stage()
    if args.stage_only:
        return
    out = outputs()
    tag = args.tag or datetime.now().strftime("v%Y%m%d-%H%M%S")
    build = BUILD.relative_to(FY26).as_posix()
    course.run(["az", "acr", "build", "--registry", out["acr_name"], "--image", f"lectures:{tag}", "--no-logs", build])
    (INFRA / "image.auto.tfvars").write_text(f'image_tag = "{tag}"\n', encoding="utf-8")
    print(f"Wrote web/infra/image.auto.tfvars: image_tag = {tag}")
    course.run(["terraform", f"-chdir={INFRA.relative_to(FY26)}", "apply", "-auto-approve", "-input=false"])
    wait_until_live(outputs()["site_url"], tag)
    print(f"\nCourse website: {outputs()['site_url']}")


if __name__ == "__main__":
    main()
