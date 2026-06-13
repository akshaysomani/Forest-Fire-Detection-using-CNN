<div align="center">

# 🔥 IgnisAI: Forest Fire Detection Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg?logo=fastapi&logoColor=white)](backend)
[![Next.js](https://img.shields.io/badge/UI-Next.js%2014-000000.svg?logo=nextdotjs&logoColor=white)](frontend)
[![PyTorch](https://img.shields.io/badge/Framework-PyTorch-EE4C2C.svg?logo=pytorch&logoColor=white)](backend)
[![Docker](https://img.shields.io/badge/Container-Docker-2496ED.svg?logo=docker&logoColor=white)](docker-compose.yml)
[![CI Pipeline](https://github.com/akshaysomani/Forest-Fire-Detection-using-CNN/actions/workflows/ci_pipeline.yml/badge.svg)](https://github.com/akshaysomani/Forest-Fire-Detection-using-CNN/actions/workflows/ci_pipeline.yml)

**An enterprise-grade, high-performance Wildfire Operations Command Interface and MLOps platform utilizing Convolutional Neural Networks (CNN) for real-time fire detection, geographic mapping, and responder mobilization.**

[Explore Docs](#-documentation-guides) • [Local Setup](#-5-minute-quickstart) • [Report Vulnerability](SECURITY.md)

</div>

---

## 🔍 Core Features Showcase

- 🧠 **PyTorch CNN Transfer Learning Factory**: Dynamic training and execution of ResNet, MobileNet, and custom CNN classification architectures for wildfire detection.
- 🗺️ **GIS Geospatial Dashboard**: Interactive Leaflet maps detailing live vector coordinates, fire-zones, and incident density overlays.
- ⚡ **Asynchronous Image Ingestion**: Deduplicated batch file uploads and ZIP archive processors via background worker tasks.
- 🔒 **DevSecOps threat Protection**: Multi-layered security checks preventing Zip-Slip traversal, SQL Injection (SQLi), and XSS script injections at the middleware layer.
- 🚨 **Incident Dispatch & Escalation**: Granular Role-Based Access Controls (RBAC) connecting Forest Officers and Responders with automated SMS/Slack alert escalations.
- 📈 **Aggregated Analytics & BI Engine**: Rollup metric summaries computed daily to load charts instantly under heavy concurrency.
- 🛠️ **Production-Ready Observability**: Pre-configured Prometheus, Grafana, Loki, and Promtail logging suites with automated SQLite/PostgreSQL backups.

---

## 📂 Repository Directory Layout

```
.
├── .github/
│   ├── workflows/            # GitHub Actions pipelines (CI, CD, Releases)
│   ├── ISSUE_TEMPLATE/       # Structured bug/feature templates
│   ├── CODEOWNERS            # Project code ownership registry
│   └── dependabot.yml        # Weekly automated security scanning rules
├── docs/                     # Modular System Guides & Manuals (REFLECTED)
│   ├── architecture.md       # Client-server request flows and layer separation
│   ├── database.md           # Declarative database schemas & ER diagrams
│   ├── api.md                # Dashboard & image endpoints specification
│   ├── ai_model.md           # CNN model factory & training configurations
│   ├── security.md           # Token rotation, rate-limiting & threat checks
│   ├── devops.md             # Docker-compose stacks, AWS IAC, K8s manifests
│   ├── testing.md            # Jest UI, Python Pytest, and k6 load targets
│   ├── monitoring.md         # Hardware telemetry metrics & SLO metrics
│   ├── alert_incident_gis.md # Geocoding vector coordinates & alerts flow
│   ├── analytics_registry.md # aggregated rollup BI engine & model registries
│   ├── troubleshooting.md    # Operations FAQ, recovery playbooks
│   └── contributing.md       # Roadmap for getting started
├── backend/                  # FastAPI Web Application & PyTorch inference
├── frontend/                 # Next.js 14 Web Command Interface
├── nginx/                    # Reverse proxy with TLS & security filters
├── ansible/                  # Server provisioning and hardening roles
├── terraform/                # AWS EC2 & RDS resource allocation scripts
├── k8s/                      # Kubernetes deployment and ingress manifests
└── tests_load/               # k6 Performance & Spike validation scripts
```

---

## 📖 Documentation Guides

We have split our system documentation into clean, modular files. Follow these guides to understand specific layers:

- **Architecture & System Design**: Read the [Architecture Guide](docs/architecture.md) and [Database Schema Guide](docs/database.md).
- **API Spec & RBAC**: Refer to [API & Access Controls Guide](docs/api.md).
- **MLOps & CNN Models**: Read [AI/ML Model & Preprocessing Guide](docs/ai_model.md) and [Model Registry Guide](docs/analytics_registry.md).
- **DevOps, K8s & Infrastructure**: Refer to [DevOps & Cloud Deployments Guide](docs/devops.md) and [Observability & Monitoring Guide](docs/monitoring.md).
- **Security & Threat Mitigation**: Refer to the [DevSecOps Security Manual](docs/security.md).
- **QA Testing Strategy**: View the [Automated Testing & Load Scripts Guide](docs/testing.md).
- **Runbooks & FAQ**: View [Troubleshooting & SRE Operations Guide](docs/troubleshooting.md).

---

## 🚀 5-Minute Quickstart

### Running Containerized Stack (Recommended)
Spin up the entire application stack including Nginx proxy, FastAPI backend, NextJS frontend, Postgres, and Redis:
```bash
# Clone the repository
git clone https://github.com/akshaysomani/Forest-Fire-Detection-using-CNN.git
cd Forest-Fire-Detection-using-CNN

# Launch development environment (SQLite-based)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```
Access the portals:
- **Frontend Command Interface**: `http://localhost:3000`
- **FastAPI Documentation**: `http://localhost:8000/docs`

For details on PostgreSQL/Redis staging environments, view [docs/devops.md](file:///c:/Users/Akshay/OneDrive/Desktop/New%20folder/Forest-Fire-Detection-using-CNN/docs/devops.md).

---

## 🤝 Contributing & Support
We welcome open-source contributions. Please read the [Contributing Guide](docs/contributing.md) to understand local setups, code validation steps, and conventions.

For support, check [SUPPORT.md](SUPPORT.md) or open a topic on our discussions board.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
