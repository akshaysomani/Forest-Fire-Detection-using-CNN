# Contributing to IgnisAI

We are thrilled that you want to contribute to IgnisAI! To ensure code quality, compliance, and enterprise-level reliability, please follow these guidelines when submitting bug reports, feature proposals, or pull requests.

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](file:///c:/Users/Akshay/OneDrive/Desktop/New%20folder/Forest-Fire-Detection-using-CNN/CODE_OF_CONDUCT.md). Please report any violations or security exploits to the maintainers at the security contact.

---

## 🛠️ Local Development Quickstart

### Prerequisites
- **Python**: version 3.11 or later
- **Node.js**: version 20 or later
- **Docker & Docker Compose**: installed and running

### Backend Setup
1. Navigate to `/backend`:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
4. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
5. Run tests to confirm the environment is healthy:
   ```bash
   python -m pytest
   ```

### Frontend Setup
1. Navigate to `/frontend`:
   ```bash
   cd ../frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Run Jest tests:
   ```bash
   npm run test
   ```
4. Run the Next.js dev server:
   ```bash
   npm run dev
   ```

---

## 🌿 Branching Strategy & Git Flow

We follow a structured branching system:
- **`main`**: Production-ready code. Never commit directly to `main`.
- **`feature/feature-name`**: New feature implementations.
- **`bugfix/bug-name`**: Fixes for reported issues.
- **`hotfix/tag-name`**: Immediate critical security patches targeting production deployments.

### Commit Messages Format
We enforce **Conventional Commits**:
- `feat: add email alert notifications on critical fire detections`
- `fix: resolve token expiry check boundary crash`
- `docs: update API setup instructions in docs/api.md`
- `chore: bump dependency version lock files`

---

## 🚀 Quality Gates & Pull Requests

Before creating a Pull Request (PR):
1. **Formatting & Linting**:
   - Backend: run `black --check backend/app` and `flake8 backend/app`.
   - Frontend: run `npm run lint`.
2. **Tests Verification**:
   - Ensure all unit, integration, and security compliance tests pass successfully.
3. **PR Templates**:
   - Complete the provided Pull Request template detailing proposed changes and test results.
   - Assign a reviewer and link the related issue.
