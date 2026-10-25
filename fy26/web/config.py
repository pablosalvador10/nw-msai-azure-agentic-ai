"""Website settings, from LECTURES_* environment variables (web/infra sets them on the Container App)."""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

FY26 = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LECTURES_", extra="ignore")

    # The site's own address. The GitHub App's callback URL is <public_url>/auth/callback.
    public_url: str = "http://localhost:8000"
    version: str = "dev"
    github_client_id: str = ""
    github_client_secret: SecretStr = SecretStr("")

    # Whoever can read this repository can use the site (owner/name).
    course_repo: str = ""
    # Links to labs, READMEs and code open on GitHub at this branch and folder.
    course_ref: str = "main"
    course_dir: str = "fy26"
    # Folder with index.html, assets/ and weekNN-*/docs/. Only those files are served.
    site_dir: Path = FY26

    # Hosts the online harness may call: student services on Azure Container Apps.
    target_host_suffixes: str = ".azurecontainerapps.io"
    max_parallel_runs: int = 3
    runs_per_hour: int = 20
    session_hours: int = 8

    def missing(self) -> list[str]:
        """Settings without which sign-in cannot work. The site refuses every request until they are set."""
        required = {
            "LECTURES_GITHUB_CLIENT_ID": self.github_client_id,
            "LECTURES_GITHUB_CLIENT_SECRET": self.github_client_secret.get_secret_value(),
            "LECTURES_COURSE_REPO": self.course_repo,
        }
        return [name for name, value in required.items() if not value]

    @property
    def secure_cookies(self) -> bool:
        return self.public_url.startswith("https://")

    @property
    def suffixes(self) -> tuple[str, ...]:
        return tuple(s.strip().lower() for s in self.target_host_suffixes.split(",") if s.strip())
