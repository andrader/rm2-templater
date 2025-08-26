import subprocess
from pathlib import Path

import typer

from rm2_templater.settings import settings


def ensure_ssh_key() -> Path:
    """Ensure a local SSH keypair exists and return the .pub path."""
    local_key = settings.remarkable_ssh_key
    pub = local_key.with_suffix(".pub")
    if not local_key.exists() or not pub.exists():
        typer.echo("🔑 No SSH key found, generating one (rsa) ...")
        local_key.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-N", "", "-f", str(local_key)], check=True
        )
    return pub
