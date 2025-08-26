from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    remarkable_ip: str = "10.11.99.1"
    remarkable_user: str = "root"
    remarkable_templates_dir: str = "/usr/share/remarkable/templates"
    remarkable_json_path: str = f"{remarkable_templates_dir}/templates.json"
    remarkable_default_category: str = "Custom"
    remarkable_icon_code: str = "\ue98c"
    remarkable_ssh_key: Path = Path.home() / ".ssh/id_rsa"
    remarkable_backup_dir: Path = Path("backups")
    remarkable_convert_dir: Path = Path("converted")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
