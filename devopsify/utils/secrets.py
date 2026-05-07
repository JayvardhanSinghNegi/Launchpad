import getpass
import subprocess
import click
from devopsify.utils.display import step, success, warn, error, info


def collect_secrets(secret_keys: list[str]) -> dict[str, str]:
    if not secret_keys:
        return {}

    click.echo(info("Collecting secret values (input hidden):"))
    secrets = {}
    for key in secret_keys:
        while True:
            value = getpass.getpass(f"    {key}: ")
            if value.strip():
                secrets[key] = value
                break
            click.echo(warn(f"    {key} cannot be empty. Try again."))
    return secrets


def push_secrets(app_name: str, secrets: dict[str, str]):
    if not secrets:
        return

    cmd = [
        "kubectl", "create", "secret", "generic",
        f"{app_name}-secrets",
        "--dry-run=client", "-o", "yaml",
    ]
    for key, value in secrets.items():
        cmd.append(f"--from-literal={key}={value}")

    # pipe through kubectl apply so it's idempotent
    dry = subprocess.run(cmd, capture_output=True, text=True)
    if dry.returncode != 0:
        raise RuntimeError(dry.stderr.strip())

    apply = subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=dry.stdout,
        capture_output=True,
        text=True,
    )
    if apply.returncode != 0:
        raise RuntimeError(apply.stderr.strip())

    click.echo(success(f"Secret '{app_name}-secrets' applied to cluster."))