# Changelog

All notable changes to the **IgnisAI Forest Fire Detection** project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-06-13

### Added
- **Quality Assurance & Testing Framework**:
  - Jest environment, mock SVG rendering configurations, and interactive NextJS component testing.
  - Pytest regression tests covering model execution accuracy tolerances, image inputs sizing/formatting, and threat detection escape routes.
  - Automated k6 load-testing configurations with HTTP latency thresholds.
- **Enterprise DevOps Architecture**:
  - Multi-stage Docker optimization configurations.
  - Nginx rate-limiting parameters, TLS config, and Gzip compression settings.
  - Terraform AWS deployment scripts.
  - Ansible provisioning playbooks.
  - Kubernetes manifests directory.
  - Prometheus, Loki, Promtail, Alertmanager observability profiles.
- **Enterprise Security & Compliance Platform**:
  - Threat detection regex engine blocking SQL Injection (SQLi) and XSS payloads.
  - IP Blacklisting parameters and client rate-limiter check.
  - Token Rotation and session reuse tracking rules.
  - Brute-force credentials lockout.
- **Geographic Intelligence Platform**:
  - Live fire-zone interactive Leaflet charts and vector bounds.
  - Incident emergency dispatcher roles, active tracking pipelines, and notification escalation.
  - CNN classifier batch inputs pipelines.

### Fixed
- Associated input form labels with active input tags using `htmlFor` and `id` keys to allow proper testing and solve accessibility limitations.
- Fixed JWT dependency imports in backend security test configurations.

---

## [0.9.0] - 2026-06-10
### Added
- Integrated CNN model training backend service with PyTorch Transfer Learning factory (`resnet18`, `mobilenet_v3`, `efficientnet_b0`).
- Implemented background thread training loops and early stopping.
- Standardized image upload APIs with ZIP extraction and MD5 deduplication.
