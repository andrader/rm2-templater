#!/usr/bin/env python3
"""
reMarkable Templates CLI

Features
- setup-ssh: generate local SSH key (if missing) and install pubkey on reMarkable
- add: convert input images to 1872x1404, 226 DPI grayscale PNG and register in templates.json
- list: list current templates with categories
- backup: download timestamped backup of templates.json
- remove: remove templates by name/filename/category, optional remote PNG deletion, all changes backed up

Requirements: pip install typer[all] paramiko pillow
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import paramiko
import typer
from loguru import logger

from rm2_templater.convert_image import convert_image, timestamp
from rm2_templater.ensure_ssh_key import ensure_ssh_key
from rm2_templater.settings import settings
from rm2_templater.Template import Template, Templates

app = typer.Typer(add_completion=False, help="Manage reMarkable templates over SSH")


# ---------- Helpers ----------


def ssh_connect(password: Optional[str] = None) -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(
            settings.remarkable_ip,
            username=settings.remarkable_user,
            password=password,
            key_filename=str(settings.remarkable_ssh_key)
            if settings.remarkable_ssh_key.exists()
            else None,
            timeout=10,
        )
    except paramiko.AuthenticationException:
        raise typer.Exit(code=1) from typer.BadParameter(
            "Authentication failed. Run `setup-ssh` first or check your key/password."
        )
    return ssh


def sftp_open(ssh: paramiko.SSHClient) -> paramiko.SFTPClient:
    return ssh.open_sftp()


def backup_remote_file(sftp: paramiko.SFTPClient, remote_path: str) -> Path:
    settings.remarkable_backup_dir.mkdir(exist_ok=True)
    local_name = f"{Path(remote_path).name}.{timestamp()}.bak"
    local_path = settings.remarkable_backup_dir / local_name
    sftp.get(remote_path, str(local_path))
    return local_path


class TemplateManager:
    def __init__(self, sftp: paramiko.SFTPClient, local_json: Path):
        self.sftp = sftp
        self.local_json = local_json

    def load_templates(self) -> Templates:
        self.sftp.get(settings.remarkable_json_path, str(self.local_json))

        try:
            with self.local_json.open("r", encoding="utf-8") as f:
                return Templates.model_validate_json(f.read())
        except json.JSONDecodeError as e:
            raise e

    def save_templates(self, data: Templates) -> None:
        # backup remote before overwrite
        backup_path = self.backup_remote_file(settings.remarkable_json_path)
        typer.echo(f"📦 Backed up templates.json to {backup_path}")
        with self.local_json.open("w", encoding="utf-8") as f:
            json.dump(data.model_dump(), f, indent=2, ensure_ascii=False)
        self.sftp.put(str(self.local_json), settings.remarkable_json_path)

    def backup_remote_file(self, remote_path: str) -> Path:
        settings.remarkable_backup_dir.mkdir(exist_ok=True)
        local_name = f"{Path(remote_path).name}.{timestamp()}.bak"
        local_path = settings.remarkable_backup_dir / local_name
        self.sftp.get(remote_path, str(local_path))
        return local_path


def restart_ui(ssh: paramiko.SSHClient) -> None:
    stdin, stdout, stderr = ssh.exec_command("systemctl restart xochitl")
    stdout.channel.recv_exit_status()


# ---------- Commands ----------


@app.command()
def setup_ssh(
    password: str = typer.Option(
        ..., prompt=True, hide_input=True, help="reMarkable root password (one-time)"
    ),
):
    """Install your local SSH public key on the reMarkable for key-based login."""
    pub_path = ensure_ssh_key()
    pubkey = pub_path.read_text().strip() + "\n"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        settings.remarkable_ip,
        username=settings.remarkable_user,
        password=password,
        timeout=10,
    )
    sftp = ssh.open_sftp()

    # Ensure ~/.ssh exists
    try:
        sftp.mkdir(".ssh")
    except IOError:
        pass

    # Append key idempotently
    try:
        content = ""
        try:
            with sftp.open(".ssh/authorized_keys", "rb") as f:
                content = f.read().decode("utf-8")
        except IOError:
            pass
        if pubkey not in content:
            with sftp.open(".ssh/authorized_keys", "a") as f:
                f.write(pubkey)
            typer.echo("✅ SSH key installed on reMarkable")
        else:
            typer.echo("ℹ️  SSH key already present on reMarkable")
    finally:
        sftp.close()
        ssh.close()


@app.command()
def add(
    paths: List[Path] = typer.Argument(
        ..., help="Template files (png/jpg/jpeg/webp) or directories"
    ),
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Additional category besides 'Custom'"
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing template entries with same filename"
    ),
    orientation: str = typer.Option(
        "auto", "--orientation", "-o", help="Output orientation: auto (default), portrait, or landscape", show_default=True
    ),
):
    """Add new template(s): converts to correct PNG, uploads, registers in templates.json."""
    ssh = ssh_connect()
    sftp = sftp_open(ssh)

    local_json = Path("templates.json")
    template_manager = TemplateManager(sftp, local_json)
    templates = template_manager.load_templates().templates

    # Ensure category folder exists on device
    try:
        sftp.mkdir(
            f"{settings.remarkable_templates_dir}/{settings.remarkable_default_category}"
        )
    except IOError:
        pass

    # Collect input files
    files: List[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend([x for x in p.iterdir() if x.is_file()])
        else:
            files.append(p)
    if not files:
        typer.echo("No input files found.")
        raise typer.Exit(code=1)

    # Convert and upload
    new_entries = []
    for f in files:
        png = convert_image(f, settings.remarkable_convert_dir, orientation=orientation)
        remote_png = f"{settings.remarkable_templates_dir}/{settings.remarkable_default_category}/{png.name}"
        sftp.put(str(png), remote_png)
        entry = {
            "name": png.stem,
            "filename": f"{settings.remarkable_default_category}/{png.stem}",  # no .png in JSON
            "iconCode": settings.remarkable_icon_code,
            "categories": [settings.remarkable_default_category]
            + ([category] if category else []),
        }
        # de-dup if exists
        existing_idx = next(
            (i for i, e in enumerate(templates) if e.filename == entry["filename"]),
            None,
        )
        if existing_idx is not None:
            if force:
                templates[existing_idx] = Template.model_validate(entry)
            else:
                typer.echo(
                    f"⚠️  Entry exists for {entry['filename']}; use --force to replace JSON record."
                )
                continue
        else:
            templates.append(Template.model_validate(entry))
        new_entries.append(entry)

    if not new_entries:
        typer.echo("Nothing to add.")
        raise typer.Exit()

    template_manager.save_templates(Templates(templates=templates))
    restart_ui(ssh)

    typer.echo(
        f"✅ Added {len(new_entries)} template(s). Categories include '{settings.remarkable_default_category}'"
        + (f" and '{category}'" if category else "")
        + "."
    )
    sftp.close()
    ssh.close()


@app.command(name="list")
def list_cmd():
    """List current templates and categories."""
    logger.debug("Listing templates")

    logger.debug("Connecting to reMarkable")
    ssh = ssh_connect()

    logger.debug("Opening SFTP connection")
    sftp = sftp_open(ssh)

    logger.debug("Loading templates.json")
    local_json = Path("templates.json")
    template_manager = TemplateManager(sftp, local_json)
    templates = template_manager.load_templates().templates

    # Pretty print
    logger.debug("Printing templates")
    typer.echo("📑 Current templates:")
    for t in templates:
        cats = ", ".join(t.categories)
        typer.echo(f"- {t.name:30}  {t.filename:40}  [{cats}]")

    logger.debug("Closing connections")
    sftp.close()
    logger.debug("Closing SSH connection")
    ssh.close()
    logger.debug("Done")


@app.command()
def backup():
    """Backup templates.json to ./backups with timestamp."""
    ssh = ssh_connect()
    sftp = sftp_open(ssh)
    b = backup_remote_file(sftp, settings.remarkable_json_path)
    typer.echo(f"📦 Saved backup: {b}")
    sftp.close()
    ssh.close()


@app.command()
def remove(
    name: Optional[str] = typer.Option(
        None, "--name", help="Remove entry by display name"
    ),
    filename: Optional[str] = typer.Option(
        None, "--filename", help="Remove by filename (e.g. Custom/my_template)"
    ),
    category: Optional[str] = typer.Option(
        None, "--category", help="Remove ALL entries in a category"
    ),
    delete_files: bool = typer.Option(
        False,
        "--delete-files",
        help="Also delete remote PNG files (backed up locally first)",
    ),
    yes: bool = typer.Option(False, "-y", help="Do not prompt for confirmation"),
):
    """Remove template entries (and optionally their PNG files) safely with backups."""
    if not any([name, filename, category]):
        typer.echo("Provide --name or --filename or --category")
        raise typer.Exit(code=2)

    ssh = ssh_connect()
    sftp = sftp_open(ssh)

    local_json = Path("templates.json")
    template_manager = TemplateManager(sftp, local_json)
    templates = template_manager.load_templates().templates

    # Select candidates
    def match(e: Template) -> bool:
        if name and e.name == name:
            return True
        if filename and e.filename == filename:
            return True
        if category and category in e.categories:
            return True
        return False

    to_remove = [e for e in templates if match(e)]
    if not to_remove:
        typer.echo("No matching templates found.")
        raise typer.Exit()

    typer.echo("These entries will be removed:")
    for e in to_remove:
        typer.echo(f"- {e.name} ({e.filename}) [{', '.join(e.categories)}]")

    if not yes:
        confirm = typer.confirm("Proceed?")
        if not confirm:
            raise typer.Exit()

    # Optionally back up and delete PNGs
    if delete_files:
        for e in to_remove:
            remote_png = f"{settings.remarkable_templates_dir}/{e.filename}.png"
            try:
                local_bak = backup_remote_file(sftp, remote_png)
                sftp.remove(remote_png)
                typer.echo(f"🗑️  Deleted {remote_png} (backup: {local_bak})")
            except IOError:
                typer.echo(f"⚠️  PNG not found for {e.filename} (skipped)")

    # Remove from JSON
    remaining = [e for e in templates if e not in to_remove]
    template_manager.save_templates(Templates(templates=remaining))
    restart_ui(ssh)

    typer.echo(f"✅ Removed {len(to_remove)} template entry(ies). UI restarted.")
    sftp.close()
    ssh.close()


if __name__ == "__main__":
    app()
