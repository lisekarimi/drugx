# =====================================
# 🌱 Project & Environment Configuration
# =====================================
# Read from pyproject.toml using grep (works on all platforms)
PROJECT_NAME = $(shell python3 -c "import re; print(re.search('name = \"(.*)\"', open('pyproject.toml').read()).group(1))")
VERSION = $(shell python3 -c "import re; print(re.search('version = \"(.*)\"', open('pyproject.toml').read()).group(1))")
-include .env
export

# Docker configuration
DOCKER_IMAGE = $(DOCKER_USERNAME)/$(PROJECT_NAME)
CONTAINER_NAME = $(PROJECT_NAME)-app
PORT ?= 8100

# =====================================
# 🐋 Docker Commands
# =====================================

build: ## Build Docker image with nginx
	docker build -t $(DOCKER_IMAGE):$(VERSION) -t $(DOCKER_IMAGE):latest .

run: ## Run with hot reloading (development mode)
	docker run -d \
		--name $(CONTAINER_NAME) \
		-p $(PORT):80 \
		-v $(PWD):/app \
		--env-file .env \
		$(DOCKER_IMAGE):latest

logs: ## View container logs
	docker logs -f $(CONTAINER_NAME)

stop: ## Stop the Docker container
	docker stop $(CONTAINER_NAME) || true

clean: stop ## Stop and remove the Docker container
	docker rm $(CONTAINER_NAME) || true

restart: clean run ## Restart Docker container (clean + run)

# =======================
# 🐳 Docker Compose Commands
# =======================

up: ## Start all services
	docker-compose up

# pgapp: ## Start app and pg services (commented - using cloud PostgreSQL)
#	docker-compose up postgres app

app: ## Start app service only (using cloud PostgreSQL)
	docker-compose up app

nb: ## Start Jupyter Notebook service
	docker-compose up jupyter

down: ## Stop all services
	docker-compose down

# db: ## Connect to local PostgreSQL (commented - using cloud PostgreSQL)
#	docker exec -it drugx-postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

# =======================
# 📊 Data Commands
# =======================

data-download: ## Download DDInter CSV files
	uvx --with requests --with pandas python data/webscraper.py

data-process: ## Process DDInter CSV files
	uvx --with pandas python data/data_processor.py

# =======================
# 🪝 Hooks
# =======================

hooks:	## Install pre-commit on local machine
	pip install pre-commit && pre-commit install && pre-commit install --hook-type commit-msg

# Pre-commit ensures code quality before commits.
# Installing globally lets you use it across all projects.
# Check if pre-commit command exists : pre-commit --version


# =====================================
# ✨ Code Quality
# =====================================

lint:	## Run code linting and formatting
	uvx ruff check .
	uvx ruff format .

fix:	## Fix code issues and format
	uvx ruff check --fix .
	uvx ruff format .


# =======================
# 🔍 Security Scanning
# =======================

# check-secrets:		## Check for secrets/API keys
# 	gitleaks detect --source . --verbose

# bandit-scan:		## Check Python code for security issues
# 	uvx bandit -r src/

# audit:	## Audit dependencies for vulnerabilities
# 	uv run --with pip-audit pip-audit

security-scan:		## Run all security checks
	gitleaks detect --source . --verbose && uv run --with pip-audit pip-audit && uvx bandit -r src/


# =======================
# 🧪 Testing Commands
# =======================

test: 	## Run all tests in the tests/ directory
	uv run --isolated --with pytest --with pytest-asyncio pytest tests/

test-file: 	## Run specific test file
	uv run --isolated --with pytest --with pytest-asyncio pytest tests/test_openfda_client.py

test-func: 	## Run specific test function by name
	uv run --isolated --with pytest --with pytest-asyncio pytest -k test_extract_code

test-cov: 	## Run tests with coverage
	uv run --isolated --with pytest --with pytest-asyncio --with pytest-cov pytest --cov=src

test-cov-html: 	## Run tests with coverage and generate HTML report
	uv run --isolated --with pytest --with pytest-asyncio --with pytest-cov pytest --cov=src --cov-report=html

open-cov: 	## Open HTML coverage report in browser
	@echo "To open the HTML coverage report, run:"
	@echo "  start htmlcov\\index.html        (Windows)"
	@echo "  open htmlcov/index.html          (macOS)"
	@echo "  xdg-open htmlcov/index.html      (Linux)"


# =======================
# ⚓ Kubernetes
# =======================

# Kubernetes deployment targets
k8s-build: ## Build and load Docker image to minikube
	docker build -t drugx:latest .
	minikube image load drugx:latest

k8s-deploy: ## Deploy to Kubernetes cluster
	kubectl apply -f k8s-deployment.yaml
	kubectl apply -f k8s-service.yaml

k8s-url: ## Get service URL
	minikube service drugx-service --url

k8s-status: ## Check deployment status
	kubectl get pods
	kubectl get services

k8s-clean: ## Delete Kubernetes resources
	kubectl delete -f k8s-service.yaml
	kubectl delete -f k8s-deployment.yaml

# =====================================
# 📚 Documentation & Help
# =====================================

help: ## Show this help message
	@echo "Available commands:"
	@echo ""
	@python3 -c "import re; lines=open('Makefile', encoding='utf-8').readlines(); targets=[re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$',l) for l in lines]; [print(f'  make {m.group(1):<20} {m.group(2)}') for m in targets if m]"


# =======================
# 🎯 PHONY Targets
# =======================

# Auto-generate PHONY targets (cross-platform)
.PHONY: $(shell python3 -c "import re; print(' '.join(re.findall(r'^([a-zA-Z_-]+):\s*.*?##', open('Makefile', encoding='utf-8').read(), re.MULTILINE)))")

# Test the PHONY generation
# test-phony:
# 	@echo "$(shell python3 -c "import re; print(' '.join(sorted(set(re.findall(r'^([a-zA-Z0-9_-]+):', open('Makefile', encoding='utf-8').read(), re.MULTILINE)))))")"
