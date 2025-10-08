# ⚙️ CI/CD
This project uses **GitHub Actions** to automate quality checks, security, and deployment.

## 🔒 Security Scan
- Runs **Gitleaks** to detect secrets in the codebase.
- Triggered on every push and pull request.
- Also included as a **pre-push hook** (via pre-commit).

Additionally, you can run all security checks manually with the Makefile:

```bash
make security-scan
````

This runs:

* 🕵️ **Gitleaks** → Detect secrets
* 📦 **pip-audit** → Check for vulnerable Python packages
* 🛡️ **Bandit** → Scan source code for security issues

👉 Use this before committing/pushing to ensure the codebase is clean.

## 🧹 Code Quality

* **Ruff** → Enforces linting and formatting standards
* **Pytest** → Runs unit tests and generates coverage reports
* Runs automatically on push, pull request, or manual trigger


## 🚀 Deployment

* Dedicated workflow to **deploy the app to Hugging Face Spaces**
* Builds Docker image, pushes it to the Space repo, and updates version
* Deployment requires manual confirmation (`workflow_dispatch`)


## 🔄 CI/CD Pipeline

![CI/CD Pipeline](https://github.com/lisekarimi/drugx/blob/main/assets/img/cicd.png?raw=true)

This diagram shows the **automated pipeline for testing, security, and deployment** of DRUGX using GitHub Actions.


## 🛡️ Local Git Hooks

This project also uses **pre-commit hooks** to catch issues early:

* Ruff lint + format at commit
* Commitizen for conventional commit messages
* Commit message length check (≤ 50 chars first line)
* Gitleaks (pre-push)
* Branch check (pre-push, prevents pushing if behind remote)

👉 Run this once to install hooks:

```bash
make hooks
```

## 🧪 Local CI Testing with act

**Prerequisites**

* Install [[Docker Desktop](https://www.docker.com/products/docker-desktop)](https://www.docker.com/products/docker-desktop)
* Install [[act](https://github.com/nektos/act)](https://github.com/nektos/act) locally

To avoid wasting GitHub Actions runner time and hours, we recommend testing workflows locally with **act**.

- act simulates GitHub Actions on your machine using Docker
- Lets you run workflows like linting, tests, and security scans before pushing
- Ensures your pipelines work exactly the same locally and remotely
- ✅ Commands are provided in `act.mk` for convenience

---

✅ Together, **CI/CD pipelines**, **pre-commit hooks**, and **local testing with `act`** ensure secure, consistent, and high-quality contributions.
