import click

CYAN   = "cyan"
GREEN  = "green"
YELLOW = "yellow"
RED    = "red"
BOLD   = True


def print_banner():
    banner = (
        "\n"
        r"  ____             ___            _  __" "\n"
        r" |  _ \  _____   _/ _ \ _ __  ___(_)/ _|_   _" "\n"
        r" | | | |/ _ \ \ / / | | | '_ \/ __| | |_| | | |" "\n"
        r" | |_| |  __/\ V /| |_| | |_) \__ \ |  _| |_| |" "\n"
        r" |____/ \___| \_/  \___/| .__/|___/_|_|  \__, |" "\n"
        r"                         |_|              |___/" "\n"
    )
    click.echo(click.style(banner, fg=CYAN, bold=BOLD))
    click.echo(click.style("  Auto DevOps. One command.\n", fg=CYAN))


def step(msg: str) -> str:
    return click.style(f"  ➜  {msg}", fg=CYAN)


def success(msg: str) -> str:
    return click.style(f"  ✔  {msg}", fg=GREEN, bold=True)


def warn(msg: str) -> str:
    return click.style(f"  ⚠  {msg}", fg=YELLOW, bold=True)


def error(msg: str) -> str:
    return click.style(f"  ✖  {msg}", fg=RED, bold=True)


def info(msg: str) -> str:
    return click.style(f"  ℹ  {msg}", fg=CYAN)


def header(msg: str) -> str:
    bar = click.style("─" * (len(msg) + 6), fg=CYAN)
    return f"\n{bar}\n  {click.style(msg, bold=True)}\n{bar}"


def confirm(msg: str):
    click.pause(info(msg))
