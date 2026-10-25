"""Helpers for the course notebooks.

Every helper prints the exact command it runs. Copy any of them into a terminal
(from the fy26/ folder) and you get the same result: nothing here is magic.
"""

import difflib
import json
import os
import platform
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

FY26 = Path(__file__).resolve().parent
INFRA = FY26 / "infra"
ENV_FILE = FY26 / ".env"

INSTALL_LINKS = {
    "uv": "https://docs.astral.sh/uv/getting-started/installation/",
    "az": "https://learn.microsoft.com/cli/azure/install-azure-cli",
    "terraform": "https://developer.hashicorp.com/terraform/install",
    "git": "https://git-scm.com/downloads",
}


def setup() -> None:
    """Run at the top of every notebook: work from fy26/ and load your .env."""
    os.chdir(FY26)
    if str(FY26) not in sys.path:
        sys.path.insert(0, str(FY26))
    if ENV_FILE.exists():
        from dotenv import load_dotenv

        load_dotenv(ENV_FILE, override=True)
    print(f"Working folder: {FY26}")
    print(f"Student:        {os.environ.get('STUDENT_ID', '(not set yet)')}")
    print(f"Model:          {os.environ.get('FOUNDRY_MODEL', '(not set yet: run the setup notebook)')}")


class Output(str):
    """A command's output. It was already printed while the command ran, so a notebook does not show it twice."""

    def _ipython_display_(self) -> None:
        pass


def run(cmd: list[str], *, check: bool = True, quiet: bool = False) -> str:
    """Run a command from fy26/, stream its output, and return it as text."""
    print("$ " + shlex.join(["python" if part == sys.executable else part for part in cmd]), flush=True)
    executable = shutil.which(cmd[0])
    if executable is None:
        raise FileNotFoundError(f"'{cmd[0]}' is not installed. See {INSTALL_LINKS.get(cmd[0], 'the setup README')}.")
    process = subprocess.Popen(
        [executable, *cmd[1:]], cwd=FY26, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    lines = []
    for line in process.stdout:  # type: ignore[union-attr]
        lines.append(line)
        if not quiet:
            print(line, end="", flush=True)
    if process.wait() != 0 and check:
        tail = "".join(lines[-15:]) if quiet else ""
        raise RuntimeError(f"Command failed (exit {process.returncode}). {tail}")
    return "".join(lines) if quiet else Output("".join(lines))


VERSION_FLAGS = {"uv": ["--version"], "az": ["version", "-o", "tsv"], "terraform": ["-version"], "git": ["--version"]}


def doctor() -> bool:
    """Check that the tools this course needs are installed and you are signed in to Azure."""
    ok = True
    print(f"{'python':10s} {platform.python_version()}  ({sys.executable})")
    for tool, args in VERSION_FLAGS.items():
        path = shutil.which(tool)
        if path is None:
            ok = False
            print(f"{tool:10s} MISSING -> install: {INSTALL_LINKS[tool]}")
            continue
        out = subprocess.run([path, *args], capture_output=True, text=True).stdout.strip().splitlines()
        print(f"{tool:10s} {out[0] if out else 'installed'}")
    if shutil.which("az"):
        account = subprocess.run([shutil.which("az"), "account", "show", "-o", "json"], capture_output=True, text=True)
        if account.returncode == 0:
            data = json.loads(account.stdout)
            print(f"\nSigned in as {data['user']['name']} | subscription '{data['name']}' ({data['id']})")
        else:
            ok = False
            print("\nNot signed in to Azure yet: run the `az login` cell.")
    return ok


def az_account() -> dict[str, Any]:
    return json.loads(run(["az", "account", "show", "-o", "json"], quiet=True))


PLACEHOLDER_STUDENT_ID = "abc1234"


def normalize_student_id(student_id: str) -> str:
    """Your NetID as Terraform needs it: 3-12 lowercase letters or digits, starting with a letter."""
    value = student_id.strip().lower()
    if value == PLACEHOLDER_STUDENT_ID:
        raise ValueError(
            f'Replace "{PLACEHOLDER_STUDENT_ID}" with your own NetID in STUDENT_ID, then run the cell again.'
        )
    if not re.fullmatch(r"[a-z][a-z0-9]{2,11}", value):
        raise ValueError(
            f"STUDENT_ID {student_id!r} is not valid: use your NetID, 3-12 letters or digits, starting with a letter."
        )
    return value


def pick_resource_group(student_id: str, requested: str, create: bool, existing: list[str]) -> tuple[str, bool]:
    """Choose where Terraform deploys: (group name, create it?). Empty name means Terraform's default group.

    A group you named is used as it exists in Azure. With no name, your class group `<netid>_resourcegroup`
    is used if you have one.
    """
    by_name = {name.lower(): name for name in existing}
    if requested.strip():
        match = by_name.get(requested.strip().lower())
        if match:
            return match, False
        if create:
            return requested.strip(), True
        close = difflib.get_close_matches(requested.strip(), existing, n=3, cutoff=0.6)
        hint = (
            f"Did you mean {' or '.join(close)}?"
            if close
            else f"Groups you can see: {', '.join(sorted(existing)[:10]) or 'none'}."
        )
        raise ValueError(
            f"Resource group {requested!r} was not found in this subscription. {hint} "
            "Check the name, or the subscription shown above."
        )
    class_group = by_name.get(f"{student_id}_resourcegroup")
    if class_group:
        return class_group, False
    return "", create


def write_tfvars(
    student_id: str, location: str = "eastus2", resource_group: str = "", create_resource_group: bool = True
) -> Path:
    """Write infra/terraform.tfvars: the inputs Terraform needs. Your subscription comes from `az account show`."""
    student_id = normalize_student_id(student_id)
    account = az_account()
    groups = json.loads(run(["az", "group", "list", "--query", "[].name", "-o", "json"], quiet=True))
    resource_group, create_resource_group = pick_resource_group(
        student_id, resource_group, create_resource_group, groups
    )
    if resource_group and not create_resource_group:
        print(f"Using your resource group: {resource_group}")
    elif create_resource_group:
        name = resource_group or f"rg-nu-{student_id}"
        print(f"Terraform will create the resource group {name}. If the class gave you one, set RESOURCE_GROUP.")
    path = INFRA / "terraform.tfvars"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    previous = re.search(r'^location\s*=\s*"([^"]+)"', existing, re.MULTILINE)
    if previous and previous.group(1) != location and (INFRA / "terraform.tfstate").exists():
        # Changing the region of resources that exist deletes and recreates all of them. Keep where they are.
        print(f"Keeping location {previous.group(1)!r}: your resources already live there.")
        location = previous.group(1)
    lines = [
        f'subscription_id       = "{account["id"]}"',
        f'student_id            = "{student_id}"',
        f'location              = "{location}"',
        f"create_resource_group = {str(create_resource_group).lower()}",
    ]
    if resource_group:
        lines.append(f'resource_group_name   = "{resource_group}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {path.relative_to(FY26)}:\n" + path.read_text())
    return path


def tf(*args: str, quiet: bool = False) -> str:
    """terraform, run against the infra/ folder."""
    return run(["terraform", f"-chdir={INFRA.relative_to(FY26)}", *args], quiet=quiet)


def outputs() -> dict[str, Any]:
    """Terraform outputs as a dict (what Terraform created: endpoints, names, URL)."""
    raw = json.loads(tf("output", "-json", quiet=True))
    return {name: item["value"] for name, item in raw.items()}


def write_env() -> Path:
    """Write fy26/.env from the Terraform outputs, so the app and notebooks find your resources."""
    out = outputs()
    values = {
        "STUDENT_ID": out["student_id"],
        "LLM_MODE": "foundry",
        "FOUNDRY_PROJECT_ENDPOINT": out["foundry_project_endpoint"],
        "FOUNDRY_OPENAI_ENDPOINT": out["foundry_openai_endpoint"],
        "FOUNDRY_MODEL": out["chat_deployment"],
        "FOUNDRY_EMBEDDING_MODEL": out["embedding_deployment"],
        "APP_URL": out.get("app_url", ""),
    }
    # Keep the Week 10 API key if .env already has one: the deployed service still requires it.
    previous = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    values.update(line.split("=", 1) for line in previous if line.startswith("SERVICE_API_KEY="))
    ENV_FILE.write_text("".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8")
    shown = "".join(f"{k}={'(hidden)' if k == 'SERVICE_API_KEY' else v}\n" for k, v in values.items())
    print(f"Wrote {ENV_FILE.name}:\n" + shown)
    setup()
    return ENV_FILE


def deploy(tag: str | None = None) -> str:
    """Build the image in your registry, point the Container App at it, and wait until it answers."""
    out = outputs()
    tag = tag or datetime.now().strftime("v%Y%m%d-%H%M%S")
    run(["az", "acr", "build", "--registry", out["acr_name"], "--image", f"app:{tag}", "--no-logs", "."])
    (INFRA / "image.auto.tfvars").write_text(f'image_tag = "{tag}"\n', encoding="utf-8")
    print(f"Wrote infra/image.auto.tfvars: image_tag = {tag}")
    tf("apply", "-auto-approve", "-input=false")
    url = outputs()["app_url"]
    _update_env("APP_URL", url)
    wait_until_live(url, tag)
    return url


def app_url() -> str:
    url = os.environ.get("APP_URL") or outputs().get("app_url", "")
    if not url:
        raise RuntimeError("No app deployed yet. Run course.deploy() first.")
    return url


def wait_until_live(url: str, version: str, timeout_s: int = 300) -> None:
    """Container Apps keeps the old revision serving until the new one is ready. Wait for the new one."""
    import httpx2

    print(f"Waiting for {url} to serve version {version} ...", end="", flush=True)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            info = httpx2.get(f"{url}/v1/info", timeout=60)
            if info.status_code == 200 and info.json().get("version") == version:
                print(" live.")
                return
        except (httpx2.HTTPError, ValueError):
            pass
        print(".", end="", flush=True)
        time.sleep(10)
    raise TimeoutError(
        f"{url} is not serving {version} yet. Check the revision: "
        "az containerapp revision list -n <app> -g <rg> -o table, and logs: az containerapp logs show -n <app> -g <rg>"
    )


def check(week: int, url: str | None = None, *, in_process: bool = False) -> dict[str, Any]:
    """Run the harness for a week (in a fresh process, so it sees your latest code). Returns the proof.

    in_process=True runs your service from the files in app/, with no server and no deploy.
    Otherwise it calls the URL (default: your deployed app). SERVICE_API_KEY, if set, is sent automatically.
    """
    command = [sys.executable, "-m", "harness", "check", "--week", str(week)]
    command += ["--in-process"] if in_process else ["--url", url or app_url()]
    output = run(command, check=False)
    match = re.search(r"Proof:\s+(\S+\.json)", output)
    if not match:
        raise RuntimeError("The harness did not finish. Read the output above.")
    return json.loads((FY26 / match.group(1)).read_text(encoding="utf-8"))


def set_api_key() -> None:
    """Week 10: generate an API key, store it for Terraform (gitignored) and for the harness (.env)."""
    key = secrets.token_urlsafe(24)
    (INFRA / "secrets.auto.tfvars").write_text(f'service_api_key = "{key}"\n', encoding="utf-8")
    _update_env("SERVICE_API_KEY", key)
    print("Wrote infra/secrets.auto.tfvars and SERVICE_API_KEY in .env (both gitignored). Deploy to apply it.")


def openai_client():
    """OpenAI client for your Foundry resource, signed in with your Azure identity (no keys)."""
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import OpenAI

    token = get_bearer_token_provider(DefaultAzureCredential(), "https://ai.azure.com/.default")
    return OpenAI(base_url=os.environ["FOUNDRY_OPENAI_ENDPOINT"], api_key=token)


def _update_env(key: str, value: str) -> None:
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    lines = [line for line in lines if not line.startswith(f"{key}=")] + [f"{key}={value}"]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[key] = value
