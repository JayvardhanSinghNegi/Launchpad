import click
from devopsify.utils.display import step, info, warn


GUIDE = """
  💡 Not sure? Use these rough guides:
     Small app  (portfolio, todo, landing page) → 250m  CPU, 256Mi RAM
     Medium app (REST API, dashboard, scraper)  → 500m  CPU, 512Mi RAM
     Heavy app  (ML model, video, data pipeline)→ 1000m CPU, 1Gi   RAM
"""

VALID_CPU    = {"250m", "500m", "1000m"}
VALID_MEMORY = {"256Mi", "512Mi", "1Gi"}


def _validate_cpu(value: str) -> str:
    value = value.strip()
    if not value:
        return "250m"
    if value not in VALID_CPU:
        click.echo(warn(f"    Unrecognised CPU value '{value}'. Accepted: {', '.join(sorted(VALID_CPU))}. Using 250m."))
        return "250m"
    return value


def _validate_memory(value: str) -> str:
    value = value.strip()
    if not value:
        return "256Mi"
    if value not in VALID_MEMORY:
        click.echo(warn(f"    Unrecognised memory value '{value}'. Accepted: {', '.join(sorted(VALID_MEMORY))}. Using 256Mi."))
        return "256Mi"
    return value


def prompt_resources() -> tuple[str, str]:
    click.echo(info(GUIDE))
    cpu = click.prompt(
        step("CPU request/limit    (250m / 500m / 1000m)"),
        default="250m",
        show_default=True,
    )
    memory = click.prompt(
        step("Memory request/limit (256Mi / 512Mi / 1Gi)"),
        default="256Mi",
        show_default=True,
    )
    return _validate_cpu(cpu), _validate_memory(memory)