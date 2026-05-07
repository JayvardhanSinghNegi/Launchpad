from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _env(subdir: str = "") -> Environment:
    path = TEMPLATES_DIR / subdir if subdir else TEMPLATES_DIR
    return Environment(
        loader=FileSystemLoader(str(path)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def _render(env: Environment, template_name: str, ctx: dict) -> str:
    return env.get_template(template_name).render(**ctx)


def generate_all(ctx: dict, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    lang = ctx["language"]

    # ── Dockerfile ───────────────────────────────────────────────────────────
    dockerfile = _render(_env(lang), "Dockerfile.j2", ctx)
    (output_dir / "Dockerfile").write_text(dockerfile)

    # ── docker-compose ────────────────────────────────────────────────────────
    dc = _render(_env(), "docker-compose.yml.j2", ctx)
    (output_dir / "docker-compose.yml").write_text(dc)

    # ── K8s ──────────────────────────────────────────────────────────────────
    k8s_dir = output_dir / "k8s"
    k8s_dir.mkdir(exist_ok=True)
    k8s_env = _env("k8s")

    for manifest in ["deployment.yaml.j2", "service.yaml.j2",
                     "ingress.yaml.j2", "hpa.yaml.j2", "configmap.yaml.j2"]:
        content = _render(k8s_env, manifest, ctx)
        (k8s_dir / manifest.replace(".j2", "")).write_text(content)

    # ── Monitoring ────────────────────────────────────────────────────────────
    mon_dir = k8s_dir / "monitoring"
    mon_dir.mkdir(exist_ok=True)
    mon_env = _env("k8s/monitoring")

    for manifest in ["prometheus.yaml.j2", "grafana.yaml.j2"]:
        content = _render(mon_env, manifest, ctx)
        (mon_dir / manifest.replace(".j2", "")).write_text(content)

    # ── Terraform ────────────────────────────────────────────────────────────
    tf_dir = output_dir / "terraform"
    tf_dir.mkdir(exist_ok=True)
    tf_env = _env("terraform")

    for tf_file in ["main.tf.j2", "variables.tf.j2", "vpc.tf.j2",
                    "eks.tf.j2", "ecr.tf.j2"]:
        content = _render(tf_env, tf_file, ctx)
        (tf_dir / tf_file.replace(".j2", "")).write_text(content)

    # ── GitHub Actions ────────────────────────────────────────────────────────
    gh_dir = output_dir / ".github" / "workflows"
    gh_dir.mkdir(parents=True, exist_ok=True)
    gh_env = _env("github")

    content = _render(gh_env, "deploy.yml.j2", ctx)
    (gh_dir / "deploy.yml").write_text(content)

    # ── README ────────────────────────────────────────────────────────────────
    readme = _render(_env(), "README.md.j2", ctx)
    (output_dir / "README.md").write_text(readme)