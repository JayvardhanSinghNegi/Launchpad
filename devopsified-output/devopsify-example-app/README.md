# devopsify-example-app

> Auto-generated DevOps setup by **DevOpsify**

## Detected Stack

| Item | Value |
|---|---|
| Language | python |
| Entry point | app.py |
| Port | 5000 |
| Database | none |
| Deploy target | minikube |
| CPU | 250m |
| Memory | 256Mi |

## Generated Structuredevopsified-output/devopsify-example-app/
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

## Run Locally

```bashdocker compose up --build

App will be available at `http://localhost:5000`

## Deploy

### minikube
```bashdevopsify deploy --repo <your-repo-url>

### AWS EKS
```bashdevopsify deploy --repo <your-repo-url> --cloud

## Secrets
No secrets detected in this app.

## Monitoring

After deploy, monitoring is available at:

| Service | Command | URL |
|---|---|---|
| Prometheus | `kubectl port-forward svc/prometheus 9090:9090` | http://localhost:9090 |
| Grafana | `kubectl port-forward svc/grafana 3000:3000` | http://localhost:3000 |

Grafana default credentials: `admin / admin`

## Manual Destroy

```bashkubectl delete -f k8s/
minikube stop
