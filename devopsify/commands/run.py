import click
import getpass
from pathlib import Path
from devopsify.utils.display import step, success, warn, error, info, header, confirm
from devopsify.utils.git import clone_repo
from devopsify.utils.detector import detect
from devopsify.utils.generator import generate_all
from devopsify.utils.secrets import collect_secrets, push_secrets
from devopsify.utils.resources import prompt_resources
from devopsify.utils.minikube import deploy_minikube
from devopsify.utils.cloud import deploy_cloud
from devopsify.utils.summary import print_arch, print_summary
from devopsify.utils.spinner import Spinner


def run(cloud: bool, repo_url: str | None):
    print_arch()

    # ── Step 1: Repo URL ────────────────────────────────────────────────────
    if not repo_url:
        repo_url = click.prompt(step("GitHub repo URL"))

    # ── Step 2: Private repo token ──────────────────────────────────────────
    is_private = click.confirm(step("Is this a private repo?"), default=False)
    github_token = None
    if is_private:
        github_token = getpass.getpass(step("GitHub personal access token: "))

    # ── Step 3: Clone ───────────────────────────────────────────────────────
    with Spinner("Cloning repository..."):
        try:
            repo_dir = clone_repo(repo_url, github_token)
        except RuntimeError as e:
            click.echo(error(f"Clone failed: {e}"))
            raise SystemExit(1)
    click.echo(success(f"Cloned to {repo_dir}"))

    # ── Step 4: Detect ──────────────────────────────────────────────────────
    click.echo(info("Running detection engine..."))
    try:
        detected = detect(repo_dir)
    except RuntimeError as e:
        click.echo(error(str(e)))
        raise SystemExit(1)

    entry_point = detected.entry_point
    if not entry_point:
        entry_point = click.prompt(
            warn("Entry point not found. Enter filename (e.g. app.py / index.js)")
        )

    port = detected.port
    if not port:
        port = click.prompt(
            warn("Port not detected. Enter port number"),
            type=int
        )

    click.echo(header("Detection Summary"))
    click.echo(info(f"  Language    : {detected.language}"))
    click.echo(info(f"  Entry point : {entry_point}"))
    click.echo(info(f"  Port        : {port}"))
    click.echo(info(f"  Secrets     : {detected.secrets or 'none'}"))
    click.echo(info(f"  DB          : {detected.db or 'none'}"))

    if not click.confirm(step("Does this look correct?"), default=True):
        click.echo(warn("Aborting. Please re-run and correct."))
        raise SystemExit(0)

    detected.entry_point = entry_point
    detected.port = port

    # ── Step 5: App name ────────────────────────────────────────────────────
    app_name = click.prompt(step("App name (used in all resource names)"))
    app_name = app_name.strip().lower().replace(" ", "-")

    # ── Step 6: Resources ───────────────────────────────────────────────────
    cpu, memory = prompt_resources()

    # ── Step 7: Secrets ─────────────────────────────────────────────────────
    secrets = {}
    if detected.secrets:
        click.echo(info(f"Found .env.example with {len(detected.secrets)} key(s): {', '.join(detected.secrets)}"))
        secrets = collect_secrets(detected.secrets)
    else:
        click.echo(warn("No .env.example found. If your app needs secrets, add them manually later."))

    # ── Step 8: DB notice ───────────────────────────────────────────────────
    if detected.db:
        click.echo(warn(
            f"DB dependency detected ({detected.db}). "
            "A demo in-cluster DB pod will be added. Not production-grade."
        ))

    # ── Step 9: Target ──────────────────────────────────────────────────────
    target = "cloud (AWS EKS)" if cloud else "minikube"
    click.echo(success(f"Deploy target: {target}"))

    # ── Step 10: Generate files ──────────────────────────────────────────────
    output_dir = Path.cwd() / "devopsified-output" / app_name
    ctx = {
        "app_name":          app_name,
        "language":          detected.language,
        "entry_point":       detected.entry_point,
        "port":              detected.port,
        "db":                detected.db,
        "has_secrets":       bool(secrets),
        "secrets":           secrets,
        "cloud":             cloud,
        "image":             f"{app_name}:latest" if not cloud else f"$ECR_REPO:{app_name}:latest",
        "image_pull_policy": "Never" if not cloud else "Always",
        "cpu":               cpu,
        "memory":            memory,
        "aws_region":        "us-east-1",
    }

    with Spinner("Generating files..."):
        generate_all(ctx, output_dir)
    click.echo(success(f"Files written to devopsified-output/{app_name}/"))

    print_summary(
        app_name=app_name,
        language=detected.language,
        port=detected.port,
        db=detected.db,
        cpu=cpu,
        memory=memory,
        cloud=cloud,
        output_dir=output_dir,
    )

    # ── Steps 11-14: Deploy + wait + destroy ────────────────────────────────
    if not cloud:
        deploy_minikube(
            app_name=app_name,
            repo_dir=detected.raw_dir,
            output_dir=output_dir,
            secrets=secrets,
        )
    else:
        deploy_cloud(
            app_name=app_name,
            repo_dir=detected.raw_dir,
            output_dir=output_dir,
            secrets=secrets,
            aws_region=ctx["aws_region"],
        )