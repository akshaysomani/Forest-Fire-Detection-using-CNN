### Step 10: Dataset Storage & Cloud Migration Guide

#### Storage Configuration Settings
Storage settings are loaded from environment variables in `.env` through [app/core/config.py](file:///c:/Users/Akshay/OneDrive/Desktop/New%20folder%20(2)/Forest-Fire-Detection-using-CNN/backend/app/core/config.py):
```bash
# Available options: local, s3, gcs, azure
STORAGE_PROVIDER="local"

# Local storage path root
STORAGE_BASE_DIR="./storage"

# Cloud storage configurations (if using stubs/future cloud adapters)
AWS_S3_BUCKET="forest-fire-detection-datasets"
GCS_BUCKET="forest-fire-detection-datasets"
AZURE_CONTAINER="forest-fire-detection-datasets"
```

#### Abstraction & Easy Migration to AWS S3 / Cloud Storage
All files are processed through the unified `StorageService` helper class. High-level application logic calls `storage_service.save_file` or `storage_service.read_file` without knowing if files are local or in a cloud bucket.

To migrate from **Local** to **AWS S3** in production:
1. Copy all folders in `./storage/datasets/` recursively to your S3 bucket root.
2. Update environment variables in your deployment setup:
   ```bash
   STORAGE_PROVIDER="s3"
   AWS_S3_BUCKET="my-production-forest-fire-datasets"
   AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
   AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
   ```
3. Restart the FastAPI server. The `StorageService` constructor will resolve the `"s3"` driver automatically on startup.

---



### Step 17: Storage Providers Configuration & Setup Guide

#### Configuration Settings (.env)
```bash
# Available Storage Providers: local, s3, gcs, azure
STORAGE_PROVIDER="local"

# Root path for local storage files (used by LocalStorageProvider)
STORAGE_BASE_DIR="./storage"

# AWS S3 Settings (used by S3StorageProvider)
AWS_S3_BUCKET="forest-fire-images-production"
AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
AWS_REGION="us-east-1"
```

- **LocalStorageProvider**: Asynchronous threadpool IO (`run_in_threadpool`) prevents event-loop blocking.
- **S3StorageProvider**: Fully asynchronous bucket management using `aioboto3` client connections. Supports generating secure, time-limited presigned URLs.
- **Local-to-Cloud Migration**: Handled by `FileStorageManager` which safely uploads files to the cloud, verifies MD5 hashes, updates databases under transaction, and deletes local copies.

---



### Step 19: Image Production Deployment & Monitoring Checklist

- [ ] **Reverse Proxy Limits**: Configure Nginx `client_max_body_size 100M;` to support large ZIP/bulk uploads.
- [ ] **Keep-Alive Timeouts**: Increase timeouts on load balancers to prevent premature network disconnects.
- [ ] **Secret Management**: Inject cloud access keys at container runtime using secure secret managers.
- [ ] **Bucket Policies**: Restrict cloud buckets to private access and enable versioning policies.
- [ ] **Disk Sweeper Alerts**: Configure alarms when disk space exceeds 85% warning / 95% critical status.

---



### Step 29: Training Production Checklist

- [ ] **GPU Execution Support**: Compile Docker container images with matching Nvidia CUDA drivers for GPU-accelerated training.
- [ ] **Docker Storage Mounts**: Ensure storage volumes (e.g., `/storage/runs`) are persistent and mounted to avoid losing weights on container updates.
- [ ] **Reverse Proxy Timeouts**: Increase Nginx read/write timeouts to handle long-running client status polling requests.
- [ ] **MLflow Logs Integration**: Configure log forwarders to forward console JSON logs to MLflow or centralized ELK stack dashboards.
- [ ] **Checkpoints Clean-up**: Setup cron routines to prune non-best checkpoints for older runs to conserve disk space.

---



## CI/CD Workflow & Docker Deployment

This project includes a fully integrated GitHub Actions workflow for CI/CD and Docker files for containerized packaging.



## Module 12: MLOps Automation, CI/CD & Deployment Orchestration Platform

This section consolidates all platform audits, reviews, manuals, deployment steps, and infrastructure guides compiled during the development of Module 12.



## IgnisAI - DevOps, MLOps & Platform Reliability Manual

This manual covers the installation, operations, monitoring, alerts routing, and recovery plans for the IgnisAI Wildfire Operations Platform.

---



### GitHub Actions
The workflow file at `.github/workflows/ci.yml` runs automatically on pushes and PRs to main. It:
1. Provisions Python 3.11 container.
2. Installs requirements.
3. Performs formatting and code checks.
4. Executes the full test suite and uploads coverage reports.





### Docker Compose Quickstart
To spin up the entire application locally in containerized form:
1. Build and launch:
   ```bash
   docker-compose up --build -d
   ```
2. The FastAPI server runs on port `8000`. Storage is persisted via named Docker volumes: `forest_fire_storage` and `forest_fire_db_data`.

---





### MLOps Container Standards





### Containerization Standards

This document specifies the security, performance, and multi-stage build rules applied to Docker container images in the Forest Fire Detection system.

---

#### 1. Multi-Stage Builds

To minimize build sizes, reduce security attack surfaces, and optimize cached layers:
*   **Builder Stage:** Installs development headers, compilers, and pip dependencies to compile wheel packages.
*   **Runner Stage:** Copies the pre-compiled packages and dependencies from the Builder stage without carrying over compilers or development tools.

---

#### 2. Security Hardening

- **Non-Root Execution:** Containers must run using a non-root system user (`appuser` with UID/GID 10001) instead of `root`.
- **Minimal Base Image:** Use `python:3.11-slim` or distroless base images to avoid unnecessary binaries (like curl, package managers) that could be exploited.
- **ReadOnly Root Filesystem compatibility:** Write logs and temp files to specific directories (e.g. `/tmp` or mounted volumes `/app/storage`) to support readonly container configurations.

---

#### 3. Performance & Startup Optimizations

- **Pyc Compilation:** Set `PYTHONDONTWRITEBYTECODE=1` and compile files if necessary to ensure rapid module loading.
- **Layer Caching:** Order steps in the Dockerfile from least frequent changes (copying `requirements.txt` and installing dependencies) to most frequent changes (copying source code).
- **Startup Probes:** Ensure the application startup scripts initialize Uvicorn with a pool of workers appropriate for the container's resource allocations.

---





### MLOps Platform Deployment Guide





### MLOps Platform Deployment Guide

This guide details steps to deploy and manage model deployments within the platform.

#### 1. Local Deployment with Docker Compose
To boot the FastAPI backend container locally:
```bash
docker-compose up --build -d
```
Verify container health:
```bash
docker ps
curl http://localhost:8000/api/v1/health
```

#### 2. Dynamic Model Deployments
To trigger a new model deployment:
```bash
curl -X POST http://localhost:8000/api/v1/deployments \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "environment_id": "<ENV_UUID>",
    "model_version_id": "<MODEL_VERSION_UUID>"
  }'
```

#### 3. Promoting Deployments
To promote an active staging model deployment to production:
```bash
curl -X POST http://localhost:8000/api/v1/deployments/promote \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_job_id": "<JOB_UUID>",
    "target_environment_id": "<PROD_ENV_UUID>"
  }'
```

#### 4. Triggering Rollbacks
To roll back staging to the previous stable release configuration:
```bash
curl -X POST http://localhost:8000/api/v1/deployments/rollback \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "environment_id": "<STAGING_ENV_UUID>"
  }'
```

---





### MLOps Platform CI/CD Guide





### MLOps Platform CI/CD Guide

This document explains the automated CI/CD pipelines configured under Github Actions.

#### 1. CI Pipeline (`ci_pipeline.yml`)
*   **Triggers:** Triggers on pull requests or commits to `main` affecting `backend/` files.
*   **Steps:**
    1.  **lint-and-format:** Runs `flake8` to scan for syntax/complexity issues and checks formatting with `black`.
    2.  **test:** Executes the complete test suite (unit and integration) using `pytest` and uploads coverage reports.
    3.  **build-check:** Dry-runs a multi-stage Docker build to ensure compilation success.

#### 2. CD Pipeline (`cd_pipeline.yml`)
*   **Triggers:** Merges to the `main` branch.
*   **Steps:**
    1.  Runs dry-runs on Terraform formatting.
    2.  Simulates Canary rollout staging deployments (traffic shifting 10% -> 50% -> 100%).
    3.  Smoke tests endpoint health.
    4.  Promotes to Production after approval validations.

#### 3. Release Pipeline (`release_pipeline.yml`)
*   **Triggers:** Git tags matching pattern `v*`.
*   **Steps:**
    1.  Builds the final release image.
    2.  Publishes release image to Github Container Registry.
    3.  Generates markdown release notes automatically from git history and creates a draft GitHub Release.

---





### MLOps Platform Infrastructure Guide





### MLOps Platform Infrastructure Guide

This document describes the Infrastructure as Code (IaC) and Kubernetes deployment blueprints.

#### 1. Terraform Blueprints (`terraform/`)
*   **main.tf:** Provisions:
    *   **VPC Security Boundaries:** Isolated public subnets for Application Load Balancers and private subnets for ECS task runners.
    *   **S3 Registry:** SSE encrypted S3 bucket for model checkpoint artifacts storage.
    *   **ECR Repository:** Secure KMS-encrypted ECR repository for hosting Docker release images.
    *   **ECS Fargate Cluster:** Serverless Fargate tasks with dedicated CloudWatch logging pipelines.
*   **variables.tf / outputs.tf:** Handles customization of CPU limits, memory boundaries, and region profiles.

#### 2. Kubernetes Blueprint (`k8s/`)
*   **configmap.yaml / secret.yaml:** Externalizes environment configurations (e.g. database connections) and maps base64-encoded credentials safely.
*   **deployment.yaml:** Spawns 2 backend replicas using a secure non-root context, mapping resource requests and liveness/readiness health probes.
*   **service.yaml / ingress.yaml:** Configures internal ClusterIP network interfaces and exposes endpoints via Nginx Ingress routing controllers.

---





### MLOps Production Readiness Checklist





### MLOps Platform Production Readiness Checklist

This document outlines the prerequisite validation checklist required before promoting this MLOps platform module to production.

- [ ] **Database Migration Seeding**
  - Verify that SQLite database schemas (`releases`, `environments`, `deployment_jobs`) have been populated.
  - Run database migrations cleanly inside targets.
- [ ] **Secret Management Configuration**
  - Rotate Vault tokens and configure KMS KMS keys.
  - Validate that secrets are prefixed with `vault::` in environment configurations.
- [ ] **Container Hardening Scans**
  - Perform vulnerability scan checks on the Docker image using tools like Trivy or Snyk.
  - Confirm the container is executed under non-root user `10001`.
- [ ] **Kubernetes Resource Boundaries**
  - Review CPU (250m req, 1 limit) and Memory (512Mi req, 2Gi limit) resources in deployment manifests.
  - Establish horizontal pod autoscaling metrics.
- [ ] **Observability & Log Sinks**
  - Map application load balancer logs to log analytics workspaces.
  - Confirm endpoints `/api/v1/deployments/observability/metrics` correctly return telemetry logs.

---



---





### Phase 18-19: Production Deployment & Checklist

#### 1. Environment Configurations (`.env.production`)
```env
NEXT_PUBLIC_API_URL=/api/v1
```

#### 2. Deployment Build Verification
Verify Next.js compiler output via:
```bash
npm run build
```
This confirms that the application has zero TypeScript compiling errors and is ready to deploy to production staging environments.


---



