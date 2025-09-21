# ACT Testing Commands
# All required environment variables are defined in the .env file
include .env
export

# Usage: make -f act.mk <target>


# =====================================
# 🔄 Continuous Integration
# =====================================

test-lint:	## Test linting workflow
	act -j lint --secret GITHUB_TOKEN=$(GITHUB_TOKEN)

test-test:	## Test unit tests workflow
	act -j test --secret GITHUB_TOKEN=$(GITHUB_TOKEN)


# =====================================
# 🚀 Continuous Delivery
# =====================================

test-hf:	## Test Hugging Face deployment
	act workflow_dispatch -W .github/workflows/deploy-hf.yml --input confirm_deployment=deploy --secret HF_USERNAME=$(HF_USERNAME) --secret HF_TOKEN=$(HF_TOKEN) --secret GITHUB_TOKEN=$(GITHUB_TOKEN) --secret GIT_USERNAME="$(GIT_USERNAME)" --secret GIT_USER_EMAIL="$(GIT_USER_EMAIL)"


# =====================================
# 📚 Documentation & Help
# =====================================

help: ## Show this help message
	@echo Available commands:
	@echo.
	@python -c "import re; lines=open('act.mk', encoding='utf-8').readlines(); targets=[re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$',l) for l in lines]; [print(f'  make {m.group(1):<20} {m.group(2)}') for m in targets if m]"

# =======================
# 🎯 PHONY Targets
# =======================

# Auto-generate PHONY targets (cross-platform)
.PHONY: $(shell python -c "import re; print(' '.join(re.findall(r'^([a-zA-Z_-]+):\s*.*?##', open('act.mk', encoding='utf-8').read(), re.MULTILINE)))")

# Test the PHONY generation
# test-phony:
# 	@echo "$(shell python -c "import re; print(' '.join(sorted(set(re.findall(r'^([a-zA-Z0-9_-]+):', open('act.mk', encoding='utf-8').read(), re.MULTILINE)))))")"
