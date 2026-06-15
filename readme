# Launchpad

> One command. A full production-style DevOps setup wrapped around any GitHub repo.

Built by **Jayvardhan Singh Negi**

---

## What it does

Launchpad takes any Python or Node.js GitHub repo and, in a single interactive run:

1. Clones the repo (public or private)
2. Detects the language, entry point, port, secrets, and database dependency
3. Generates a complete DevOps setup around it:
   - Dockerfile (language specific)
   - Kubernetes manifests Deployment, Service, Ingress, HPA, ConfigMap
   - Prometheus + Grafana monitoring
   - Terraform infrastructure VPC, EKS, ECR
   - GitHub Actions CI/CD pipeline
4. Deploys it to **minikube** locally, or **AWS EKS** with `--cloud`
5. Prints the live URL
6. Waits for you, then auto-destroys everything on confirmation


---

## Requirements

### On your machine

| Tool | Version | Install |
|---|---|---|
| Python | 3.10+ | pre-installed |
| Docker | any | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Git | any | pre-installed |
| minikube | latest | [minikube.sigs.k8s.io](https://minikube.sigs.k8s.io/docs/start/) |
| kubectl | latest | [kubernetes.io](https://kubernetes.io/docs/tasks/tools/) |

### For `--cloud` only

| Tool | Install |
|---|---|
| Terraform | [developer.hashicorp.com/terraform/install](https://developer.hashicorp.com/terraform/install) |
| AWS CLI | [aws.amazon.com/cli](https://aws.amazon.com/cli/) |


## Installation

```bash
git clone https://github.com/JayvardhanSinghNegi/Launchpad
cd Launchpad
pip install -e .
```

Verify:

```bash
launchpad --help
```

---

## Usage

### Local (minikube)

```bash
launchpad deploy --repo https://github.com/<user>/<repo>
```

### Cloud (AWS EKS)

```bash
launchpad deploy --repo https://github.com/<user>/<repo> --cloud
```

### Fully interactive

Skip `--repo` and Launchpad will prompt you for the URL (and ask whether it's a private repo, prompting for a GitHub token if so):

```bash
launchpad deploy
```

Both flags are optional: `--repo` skips the URL prompt, `--cloud` switches the target from minikube to AWS EKS.

---

## Interactive flow

When you run `launchpad deploy`, it walks you through:

```
1.  GitHub repo URL
2.  Is it private?  (token prompt if yes)
3.  Clone + run the detection engine
4.  Detection summary → confirm  (prompts for entry point / port if not auto-detected)
5.  App name  (used for all resource names)
6.  CPU + memory  (with a helper guide)
7.  Secret values from .env.example  (hidden input)
8.  DB notice, if a database dependency was detected
9.  Confirm deploy target
10. Generate all files → devopsified-output/<app-name>/
11. Deploy
12. Show live URL (+ Grafana link)
13. Press Enter once you've seen the demo
14. Everything auto-destroyed → clean slate
```

---

## Resource guide

When prompted for CPU and memory, accepted values are fixed presets:

```
Small app  (portfolio, todo, landing page)  → 250m  CPU, 256Mi RAM
Medium app (REST API, dashboard, scraper)   → 500m  CPU, 512Mi RAM
Heavy app  (ML model, video, data pipeline) → 1000m CPU, 1Gi   RAM
```

Anything outside `250m / 500m / 1000m` (CPU) or `256Mi / 512Mi / 1Gi` (memory) falls back to the small preset.

---

## Generated output

```
devopsified-output/
└── <app-name>/
    ├── Dockerfile
    ├── docker-compose.yml
    ├── README.md
    ├── k8s/
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── ingress.yaml
    │   ├── hpa.yaml
    │   ├── configmap.yaml
    │   └── monitoring/
    │       ├── prometheus.yaml
    │       └── grafana.yaml
    ├── terraform/
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── vpc.tf
    │   ├── eks.tf
    │   └── ecr.tf
    └── .github/
        └── workflows/
            └── deploy.yml
```

A sample of this output is checked into the repo under `devopsified-output/devopsify-example-app/` so you can see exactly what gets generated without running a deploy.

---

## Detection

Launchpad's detection engine (`devopsify/utils/detector.py`) figures out:

| Signal | How it's detected |
|---|---|
| **Language** | `requirements.txt` → Python, `package.json` → Node.js |
| **Entry point** | First match among `main.py / app.py / run.py / wsgi.py / asgi.py` (Python) or `index.js / server.js / app.js / main.js` (Node) — prompts if none found |
| **Port** | Regex scan of the entry file and common config files (`app.run(port=…)`, `.listen(…)`, `PORT=…`, etc.) — prompts if not found |
| **Secrets** | Keys parsed from `.env.example` |
| **Database** | Postgres (`psycopg2`, `sqlalchemy`, `pg`, `mysql2`) or Mongo (`pymongo`, `mongoose`) from the dependency manifest |

When a DB dependency is found, a **demo in-cluster DB pod** is added to the manifests. It's for demos, not production.

---

## Monitoring

After deploy, Launchpad applies the Prometheus and Grafana manifests into the cluster, then **auto port-forwards Grafana**:

| Service | Access | Credentials |
|---|---|---|
| Grafana | `http://localhost:3000` (auto port-forwarded) | admin / admin |
| Prometheus | deployed in-cluster — port-forward manually with `kubectl port-forward svc/prometheus 9090:9090` | — |

Both monitoring manifests are deleted during cleanup.

---

## Secrets

- Detected from `.env.example` in your repo
- Collected via hidden input (`getpass`) — values are never echoed
- Pushed into the cluster with `kubectl create secret` (rendered with `--dry-run=client` and piped to `kubectl apply`, so it's idempotent)
- Never written to a file on disk

---

## Supported languages

| Language | Detection signal |
|---|---|
| Python | `requirements.txt` |
| Node.js | `package.json` |

---

## Not supported (v1)

- Languages beyond Python and Node.js
- Monorepos or multi-service repos
- KMS / Vault / external secret managers
- Multi-region deploys
- IAM provisioned as standalone Terraform (EKS-managed roles only)

---

## Architecture

```
GitHub Repo
    │
    ▼
┌─────────┐     ┌────────────┐     ┌───────────────┐
│  Clone  │────▶│  Detect    │────▶│ Generate Files│
└─────────┘     └────────────┘     └───────┬───────┘
                                           │
            ┌──────────────────────────────┤
            │                              │
            ▼                              ▼
     ┌─────────────┐              ┌──────────────────┐
     │   minikube  │              │   AWS EKS (cloud)│
     │─────────────│              │──────────────────│
     │ docker build│              │ terraform apply  │
     │ kubectl apply│             │ ECR push         │
     │ port-forward│              │ kubectl apply    │
     └──────┬──────┘              └────────┬─────────┘
            │                              │
            └──────────────┬───────────────┘
                           │
                           ▼
                ┌────────────────────┐
                │ Prometheus+Grafana │
                │ HPA autoscaling    │
                │ Secrets injected   │
                └────────┬───────────┘
                         │
                         ▼
                ┌────────────────────┐
                │   Demo running     │
                │   Auto-destroy     │
                └────────────────────┘
```

---

## Project structure

```
Launchpad/
├── setup.py
├── requirements.txt
├── README.md
├── devopsified-output/               ← sample generated output (example)
│   └── devopsify-example-app/
└── devopsify/                        ← the Python package (CLI: launchpad)
    ├── main.py                       ← click entry point: `launchpad deploy`
    ├── commands/
    │   └── run.py                    ← orchestrates the full flow
    ├── utils/
    │   ├── display.py
    │   ├── git.py
    │   ├── detector.py
    │   ├── generator.py
    │   ├── secrets.py
    │   ├── resources.py
    │   ├── minikube.py
    │   ├── cloud.py
    │   ├── monitoring.py
    │   ├── spinner.py
    │   └── summary.py
    └── templates/
        ├── README.md.j2
        ├── docker-compose.yml.j2
        ├── python/Dockerfile.j2
        ├── node/Dockerfile.j2
        ├── k8s/
        │   ├── deployment.yaml.j2
        │   ├── service.yaml.j2
        │   ├── ingress.yaml.j2
        │   ├── hpa.yaml.j2
        │   ├── configmap.yaml.j2
        │   └── monitoring/
        │       ├── prometheus.yaml.j2
        │       └── grafana.yaml.j2
        ├── terraform/
        │   ├── main.tf.j2
        │   ├── variables.tf.j2
        │   ├── vpc.tf.j2
        │   ├── eks.tf.j2
        │   └── ecr.tf.j2
        └── github/
            └── deploy.yml.j2
```

---

*Built by Jayvardhan Singh Negi*
