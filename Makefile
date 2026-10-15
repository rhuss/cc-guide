.PHONY: validate install uninstall reinstall test test-adapters eval help

MARKETPLACE := guide-plugin-development
PLUGIN := guide@$(MARKETPLACE)
ADAPTER_TESTS := $(wildcard tests/adapters/test_*.sh)

validate:
	claude plugin validate ./
	claude plugin validate ./guide/

install:
	@# Add or update the marketplace
	@if claude plugin marketplace add ./ 2>&1 | grep -q "already"; then \
		echo "Updating marketplace..."; \
		claude plugin marketplace update $(MARKETPLACE); \
	else \
		echo "Marketplace added."; \
	fi
	@# Install or reinstall the plugin
	@if claude plugin list 2>/dev/null | grep -q "$(PLUGIN)"; then \
		echo "Plugin already installed, reinstalling..."; \
		claude plugin rm $(PLUGIN) 2>/dev/null || true; \
	fi
	claude plugin install $(PLUGIN)

uninstall:
	@echo "Removing plugin..."
	@claude plugin rm $(PLUGIN) 2>/dev/null || echo "Plugin not installed"
	@echo "Removing marketplace..."
	@claude plugin marketplace rm $(MARKETPLACE) 2>/dev/null || echo "Marketplace not installed"

reinstall: uninstall install

test:
	uv run --no-project --with pytest --with pyyaml --with pypdf --with pillow --with 'fonttools[woff]==4.67.0' pytest tests/toolkit

test-adapters:
	@fail=0; for t in $(ADAPTER_TESTS); do \
		echo "== $$t"; \
		bash $$t || fail=1; \
	done; exit $$fail

eval:
	@echo "The behavioral evals run through the agent-eval-harness plugin inside Claude Code:"
	@echo "  export CC_GUIDE_PLUGIN=\"$(CURDIR)/guide\""
	@echo "  /eval-run        (reads eval.yaml, cases under eval/cases/)"
	@uv run --no-project --with pyyaml python -c "import yaml,sys; c=yaml.safe_load(open('eval.yaml')); print('eval.yaml OK:', c['name'])"

help:
	@echo "Available targets:"
	@echo "  validate       - Validate the marketplace and plugin manifests"
	@echo "  install        - Install or update the plugin (idempotent)"
	@echo "  uninstall      - Remove the plugin and the marketplace"
	@echo "  reinstall      - Full reinstall (uninstall + install)"
	@echo "  test           - Run the toolkit tests (pytest through uv)"
	@echo "  test-adapters  - Run the adapter smoke tests (tests/adapters/test_*.sh)"
	@echo "  eval           - Run the behavioral evaluation suite (eval.yaml)"
