import subprocess
import time
import click
from devopsify.utils.display import success, info, warn


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def _wait_for_pod(label: str, timeout: int = 120):
    click.echo(info(f"Waiting for {label} pod to be ready..."))
    r = subprocess.run(
        [
            "kubectl", "wait", "pod",
            "-l", f"app={label}",
            "--for=condition=Ready",
            f"--timeout={timeout}s",
        ],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        click.echo(warn(f"{label} pod not ready in time. Skipping port-forward."))
        return False
    return True


def deploy_monitoring(k8s_dir):
    mon_dir = k8s_dir / "monitoring"
    if not mon_dir.exists():
        click.echo(warn("Monitoring manifests not found. Skipping."))
        return

    click.echo(info("Deploying Prometheus..."))
    r = _run(["kubectl", "apply", "-f", str(mon_dir / "prometheus.yaml")])
    if r.returncode != 0:
        click.echo(warn(f"Prometheus apply failed:\n{r.stderr.strip()}"))

    click.echo(info("Deploying Grafana..."))
    r = _run(["kubectl", "apply", "-f", str(mon_dir / "grafana.yaml")])
    if r.returncode != 0:
        click.echo(warn(f"Grafana apply failed:\n{r.stderr.strip()}"))

    click.echo(info("Monitoring stack deployed."))


def start_grafana_portforward() -> subprocess.Popen | None:
    if not _wait_for_pod("grafana"):
        return None

    click.echo(info("Port-forwarding Grafana → http://localhost:3000  (admin / admin)"))
    proc = subprocess.Popen(
        ["kubectl", "port-forward", "svc/grafana", "3000:3000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)
    if proc.poll() is not None:
        click.echo(warn("Grafana port-forward exited immediately. Check kubectl logs."))
        return None

    click.echo(success("Grafana available at http://localhost:3000  (admin / admin)"))
    return proc


def stop_monitoring(pf_proc: subprocess.Popen | None):
    if pf_proc and pf_proc.poll() is None:
        pf_proc.terminate()
        click.echo(info("Grafana port-forward stopped."))

    click.echo(info("Deleting monitoring resources..."))
    for manifest in ["prometheus.yaml", "grafana.yaml"]:
        subprocess.run(
            ["kubectl", "delete", "-f", f"k8s/monitoring/{manifest}", "--ignore-not-found=true"],
            capture_output=True,
        )