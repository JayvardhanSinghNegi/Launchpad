import subprocess
import shutil
import click
from pathlib import Path
from devopsify.utils.display import step, success, warn, error, info
from devopsify.utils.secrets import push_secrets
from devopsify.utils.monitoring import deploy_monitoring, start_grafana_portforward, stop_monitoring
from devopsify.utils.spinner import Spinner


def _run(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=capture, text=True)


def _require(binary: str):
    if not shutil.which(binary):
        raise RuntimeError(
            f"'{binary}' not found. Install it and re-run.\n"
            f"  minikube: https://minikube.sigs.k8s.io/docs/start/\n"
            f"  kubectl:  https://kubernetes.io/docs/tasks/tools/"
        )


def _minikube_running() -> bool:
    r = _run(["minikube", "status"])
    return "Running" in r.stdout


def _start_minikube():
    with Spinner("Starting minikube..."):
        r = subprocess.run(
            ["minikube", "start", "--driver=docker"],
            capture_output=True, text=True,
        )
    if r.returncode != 0:
        raise RuntimeError(f"minikube start failed.\n{r.stderr.strip()}")
    click.echo(success("minikube started."))


def _docker_env() -> dict[str, str]:
    r = _run(["minikube", "docker-env", "--shell=bash"])
    if r.returncode != 0:
        raise RuntimeError("Could not get minikube docker-env.")
    env = {}
    for line in r.stdout.splitlines():
        if line.startswith("export "):
            line = line[len("export "):]
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip().strip('"')
    import os
    merged = os.environ.copy()
    merged.update(env)
    return merged


def _build_image(app_name: str, repo_dir: Path, docker_env: dict):
    click.echo(info(f"Building image {app_name}:latest inside minikube Docker..."))
    r = subprocess.run(
        ["docker", "build", "-t", f"{app_name}:latest", str(repo_dir)],
        env=docker_env,
        capture_output=False,
        text=True,
    )
    if r.returncode != 0:
        raise RuntimeError("docker build failed.")
    click.echo(success(f"Image {app_name}:latest built."))


def _kubectl_apply(k8s_dir: Path):
    click.echo(info("Applying K8s manifests..."))
    r = _run(["kubectl", "apply", "-f", str(k8s_dir)])
    if r.returncode != 0:
        raise RuntimeError(f"kubectl apply failed:\n{r.stderr.strip()}")
    click.echo(success("Manifests applied."))


def _rollout_wait(app_name: str):
    with Spinner(f"Waiting for rollout of {app_name}..."):
        r = subprocess.run(
            ["kubectl", "rollout", "status",
             f"deployment/{app_name}", "--timeout=120s"],
            capture_output=True, text=True,
        )
    if r.returncode != 0:
        raise RuntimeError("Rollout did not complete in time.")
    click.echo(success(f"{app_name} rollout complete."))


def _get_url(app_name: str) -> str:
    r = _run(["minikube", "service", app_name, "--url"])
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError("Could not retrieve service URL.")
    return r.stdout.strip().splitlines()[0]


def _destroy(k8s_dir: Path, app_name: str):
    click.echo(info("Deleting K8s resources..."))
    _run(["kubectl", "delete", "-f", str(k8s_dir), "--ignore-not-found=true"])
    _run(["kubectl", "delete", "secret", f"{app_name}-secrets", "--ignore-not-found=true"])
    click.echo(success("Resources deleted."))


def _stop_minikube():
    click.echo(info("Stopping minikube..."))
    _run(["minikube", "stop"])
    click.echo(success("minikube stopped."))


def deploy_minikube(app_name: str, repo_dir: Path, output_dir: Path, secrets: dict):
    _require("minikube")
    _require("kubectl")
    _require("docker")

    if not _minikube_running():
        _start_minikube()
    else:
        click.echo(info("minikube already running."))

    docker_env = _docker_env()
    import shutil
    shutil.copy(output_dir / "Dockerfile", repo_dir / "Dockerfile")
    _build_image(app_name, repo_dir, docker_env)
    k8s_dir = output_dir / "k8s"
    _kubectl_apply(k8s_dir)
    deploy_monitoring(k8s_dir)
    pf_proc = start_grafana_portforward()

    if secrets:
        try:
            push_secrets(app_name, secrets)
        except RuntimeError as e:
            click.echo(error(f"Secret push failed: {e}"))

    _rollout_wait(app_name)

    try:
        url = _get_url(app_name)
        click.echo(success(f"App is live at: {url}"))
    except RuntimeError as e:
        click.echo(warn(str(e)))

    click.prompt(click.style("\n  ↵  Press Enter once you've seen the demo to auto-destroy everything...", fg="yellow"), default="", show_default=False)


    stop_monitoring(pf_proc)
    _destroy(k8s_dir, app_name)
    _stop_minikube()
    click.echo(success("All resources destroyed. Clean slate."))
    _destroy(k8s_dir, app_name)
    _stop_minikube()
    click.echo(success("All resources destroyed. Clean slate."))