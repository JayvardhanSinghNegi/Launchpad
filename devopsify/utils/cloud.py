import subprocess
import shutil
import json
import click
from pathlib import Path
from devopsify.utils.display import success, warn, error, info
from devopsify.utils.secrets import push_secrets
from devopsify.utils.monitoring import deploy_monitoring, start_grafana_portforward, stop_monitoring
from devopsify.utils.spinner import Spinner


def _run(cmd: list[str], capture: bool = True, cwd: Path = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=capture, text=True, cwd=cwd)


def _require(binary: str):
    if not shutil.which(binary):
        raise RuntimeError(
            f"'{binary}' not found.\n"
            f"  terraform: https://developer.hashicorp.com/terraform/install\n"
            f"  kubectl:   https://kubernetes.io/docs/tasks/tools/\n"
            f"  aws:       https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
        )


def _log_resources(output_dir: Path, ecr_url: str, cluster_name: str):
    log = output_dir / "destroy.log"
    log.write_text(
        f"ecr_repo_url={ecr_url}\n"
        f"cluster_name={cluster_name}\n"
    )
    click.echo(info(f"Resource IDs logged to {log}"))


def _terraform_init_apply(tf_dir: Path) -> dict:
    with Spinner("Running terraform init..."):
        r = subprocess.run(
            ["terraform", "init", "-input=false"],
            capture_output=True, text=True, cwd=tf_dir,
        )
    if r.returncode != 0:
        raise RuntimeError(f"terraform init failed.\n{r.stderr.strip()}")
    click.echo(success("terraform init complete."))

    with Spinner("Running terraform apply (this takes ~10 min)..."):
        r = subprocess.run(
            ["terraform", "apply", "-auto-approve", "-input=false"],
            capture_output=True, text=True, cwd=tf_dir,
        )
    if r.returncode != 0:
        raise RuntimeError(f"terraform apply failed.\n{r.stderr.strip()}")
    click.echo(success("terraform apply complete."))

    r = _run(["terraform", "output", "-json"], cwd=tf_dir)
    if r.returncode != 0:
        raise RuntimeError("terraform output failed.")
    return json.loads(r.stdout)


def _ecr_login(ecr_url: str, aws_region: str):
    click.echo(info("Logging in to ECR..."))
    pwd = _run(
        ["aws", "ecr", "get-login-password", "--region", aws_region]
    )
    if pwd.returncode != 0:
        raise RuntimeError("aws ecr get-login-password failed.")
    registry = ecr_url.split("/")[0]
    login = subprocess.run(
        ["docker", "login", "--username", "AWS", "--password-stdin", registry],
        input=pwd.stdout,
        capture_output=True,
        text=True,
    )
    if login.returncode != 0:
        raise RuntimeError(f"docker login failed: {login.stderr.strip()}")
    click.echo(success("ECR login successful."))


def _build_and_push(app_name: str, ecr_url: str, repo_dir: Path, image_tag: str):
    local_tag = f"{app_name}:latest"
    remote_tag = f"{ecr_url}:{image_tag}"

    click.echo(info(f"Building image {local_tag}..."))
    r = _run(["docker", "build", "-t", local_tag, str(repo_dir)], capture=False)
    if r.returncode != 0:
        raise RuntimeError("docker build failed.")

    click.echo(info(f"Tagging as {remote_tag}..."))
    _run(["docker", "tag", local_tag, remote_tag])

    click.echo(info(f"Pushing {remote_tag}..."))
    r = _run(["docker", "push", remote_tag], capture=False)
    if r.returncode != 0:
        raise RuntimeError("docker push failed.")
    click.echo(success(f"Image pushed to ECR: {remote_tag}"))
    return remote_tag


def _update_kubeconfig(cluster_name: str, aws_region: str):
    click.echo(info(f"Updating kubeconfig for cluster {cluster_name}..."))
    r = _run([
        "aws", "eks", "update-kubeconfig",
        "--name", cluster_name,
        "--region", aws_region,
    ], capture=False)
    if r.returncode != 0:
        raise RuntimeError("aws eks update-kubeconfig failed.")


def _kubectl_apply(k8s_dir: Path):
    click.echo(info("Applying K8s manifests..."))
    r = _run(["kubectl", "apply", "-f", str(k8s_dir)])
    if r.returncode != 0:
        raise RuntimeError(f"kubectl apply failed:\n{r.stderr.strip()}")
    click.echo(success("Manifests applied."))


def _rollout_wait(app_name: str):
    click.echo(info(f"Waiting for rollout of {app_name}..."))
    r = _run(
        ["kubectl", "rollout", "status", f"deployment/{app_name}", "--timeout=180s"],
        capture=False,
    )
    if r.returncode != 0:
        raise RuntimeError("Rollout did not complete in time.")


def _get_lb_url(app_name: str) -> str:
    import time
    click.echo(info("Waiting for LoadBalancer IP/hostname (up to 3 min)..."))
    for _ in range(18):
        r = _run([
            "kubectl", "get", "svc", app_name,
            "-o", "jsonpath={.status.loadBalancer.ingress[0].hostname}",
        ])
        host = r.stdout.strip()
        if host:
            return f"http://{host}"
        time.sleep(10)
    raise RuntimeError("LoadBalancer hostname not assigned in time. Check: kubectl get svc")


def _destroy_k8s(k8s_dir: Path, app_name: str):
    click.echo(info("Deleting K8s resources..."))
    _run(["kubectl", "delete", "-f", str(k8s_dir), "--ignore-not-found=true"])
    _run(["kubectl", "delete", "secret", f"{app_name}-secrets", "--ignore-not-found=true"])
    click.echo(success("K8s resources deleted."))


def _terraform_destroy(tf_dir: Path, output_dir: Path):
    click.echo(info("Running terraform destroy..."))
    r = _run(["terraform", "destroy", "-auto-approve", "-input=false"], capture=False, cwd=tf_dir)
    if r.returncode != 0:
        click.echo(error(
            "terraform destroy failed. Check destroy.log for resource IDs.\n"
            "Manual destroy command:\n"
            f"  cd {tf_dir} && terraform destroy"
        ))
    else:
        click.echo(success("All cloud infrastructure destroyed."))
        destroy_log = output_dir / "destroy.log"
        if destroy_log.exists():
            destroy_log.unlink()


def deploy_cloud(
    app_name: str,
    repo_dir,
    output_dir: Path,
    secrets: dict,
    aws_region: str,
    image_tag: str = "latest",
):
    for binary in ["terraform", "kubectl", "docker", "aws"]:
        _require(binary)

    tf_dir  = output_dir / "terraform"
    k8s_dir = output_dir / "k8s"
    cluster_name = f"{app_name}-eks"

    # log resource IDs before anything is created (safety net)
    click.echo(info("Logging resource identifiers to destroy.log before deploy..."))
    _log_resources(output_dir, ecr_url="<pending>", cluster_name=cluster_name)
    click.echo(warn(
        f"If anything goes wrong run:\n"
        f"  cd {tf_dir} && terraform destroy"
    ))

    tf_outputs = _terraform_init_apply(tf_dir)

    ecr_url = tf_outputs.get("ecr_repo_url", {}).get("value", "")
    if not ecr_url:
        raise RuntimeError("Could not read ecr_repo_url from terraform output.")

    # update destroy.log with real ECR URL now we have it
    _log_resources(output_dir, ecr_url=ecr_url, cluster_name=cluster_name)

    _ecr_login(ecr_url, aws_region)
    remote_image = _build_and_push(app_name, ecr_url, repo_dir, image_tag)
    _update_kubeconfig(cluster_name, aws_region)
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
        url = _get_lb_url(app_name)
        click.echo(success(f"App is live at: {url}"))
    except RuntimeError as e:
        click.echo(warn(str(e)))

    click.pause(click.style("\n  ↵  Press Enter once you've seen the demo to auto-destroy everything...", fg="yellow"))

    stop_monitoring(pf_proc)
    _destroy_k8s(k8s_dir, app_name)
    _terraform_destroy(tf_dir, output_dir)
    click.echo(success("All resources destroyed. Clean slate."))
    _destroy_k8s(k8s_dir, app_name)
    _terraform_destroy(tf_dir, output_dir)
    click.echo(success("All resources destroyed. Clean slate."))