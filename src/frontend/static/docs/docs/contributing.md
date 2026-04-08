# 🤝 Contributing
We welcome contributions to DRUGX! Please follow these guidelines:

## 🧹 Code Style
- Use **Ruff** for linting and formatting.
- Keep code clean, simple, and well-documented.

## 📝 Commits
- Follow **Conventional Commits** (enforced via Commitizen).
- Keep commit messages clear and concise.

## 🔒 Security
- Run `make security-scan` before pushing to catch secrets, vulnerabilities, and code issues.
- Pre-commit hooks (Gitleaks, commit checks) must be installed with:
  ```bash
  make hooks
  ```

## 📦 Dependencies

* All dependencies must be declared in **pyproject.toml**.
* Keep them organized by extras (`app`, `test`, etc.).
* Update versions responsibly.

## 📝 Versioning & Changelog

* Update the **version** in `pyproject.toml` when needed.
* Reflect changes in **CHANGELOG.md**.

## 🧪 Testing

* Write **Pytest** unit tests for new logic.
* Ensure `make test` passes before opening a PR.
* Focus tests on **business logic**, not Streamlit UI.
* Maintain at least **65% coverage** for the model and application logic.
* UI components (Streamlit) are intentionally excluded from coverage.

---

✅ All contributions are automatically validated by the **CI/CD pipeline** (linting, tests, security, deployment).
