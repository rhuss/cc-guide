# Guide build, MkDocs Material adapter (cc-guide). Every version, commit, and permalink
# comes from baseline.yaml through tools/guide/mkdocs_macros.py; pages never type them.
# Targets and their semantics are identical across adapters (contracts/adapter.md).
# MkDocs and its plugins run through uvx with the pins in requirements.txt (never pip).
SHELL := /bin/bash
UV ?= uv
UVX ?= uvx
TOOLS := tools/guide
STRICT ?= 0
VIEW ?= shareable
PORT ?= 8000
# make preview opens the browser; OPEN=0 only serves
# (the preview skill opens it itself).
OPEN ?= 1
MKDOCS := $(UVX) --quiet --with-requirements requirements.txt mkdocs

GET = $(UV) run --quiet $(TOOLS)/guidecfg.py get
# The PDF file for a view (shareable or internal), as the shell variable out.
PDF_OUT = slug=$$($(GET) slug) && date=$$($(GET) baseline.captured) || exit 1; \
	if [ "$(1)" = internal ]; then out=dist/$$slug-$$date-INTERNAL.pdf; else out=dist/$$slug-$$date.pdf; fi
# The print-site page: one section per navigation group (h1 without id) holding one
# section per page (h1); the site chrome is removed before printing.
PRINT_ARGS = --page-heading 'section.print-page[id]:not(.md-section) > h1' \
	--section-heading 'section.md-section > h1' \
	--hide '.md-header, .md-tabs, .md-sidebar, .md-footer, .md-search, .md-skip, .md-overlay, .md-dialog, .md-top, .print-page-toc-title'

# MkDocs Material 9.7 prints a banner about MkDocs 2.0 on every build; the pins keep 1.6.
export NO_MKDOCS_2_WARNING := true

.PHONY: help doctor fetch-baseline site site-internal check preview pdf print-pdf dist drift clean

help:
	@echo "Guide targets (MkDocs Material adapter):"
	@echo "  make doctor          check the tool chain"
	@echo "  make fetch-baseline  fetch the pinned sources into .guide/cache/"
	@echo "  make site            build the shareable view into build/site"
	@echo "  make site-internal   build the internal view into build/site-internal"
	@echo "  make check           builds, page and content checks, leak check (STRICT=1 adds the claim ledger)"
	@echo "  make preview         serve with live reload (VIEW=internal for the internal view, PORT=$(PORT))"
	@echo "  make pdf             one PDF of the guide (VIEW=internal for the internal view)"
	@echo "  make dist            check, then the PDF(s) and the shareable tarball (and the internal ones when enabled)"
	@echo "  make drift           compare the baseline with the sources (exit 10 on drift)"

node_modules:
	npm install

doctor:
	$(UV) run --quiet $(TOOLS)/doctor.py

fetch-baseline:
	$(UV) run --quiet $(TOOLS)/fetch.py fetch

site:
	$(MKDOCS) build --strict --clean -f mkdocs.yml

site-internal:
	@if [ "$$($(GET) internal.enabled)" != true ]; then \
		echo "internal part disabled in guide.yaml; skipping site-internal"; \
	else \
		$(MKDOCS) build --strict --clean -f mkdocs-internal.yml; \
	fi

check: fetch-baseline site site-internal
	$(UV) run --quiet $(TOOLS)/guidecfg.py validate
	STRICT=$(STRICT) $(UV) run --quiet $(TOOLS)/check.py
	@if [ "$(STRICT)" = 1 ]; then $(UV) run --quiet $(TOOLS)/ledger.py; fi
	$(UV) run --quiet $(TOOLS)/leakcheck.py build/site

preview: node_modules
	node $(TOOLS)/preview-watch.mjs $(if $(filter internal,$(VIEW)),--internal) $(if $(filter 0,$(OPEN)),--no-open) --port $(PORT)

pdf:
	@$(call PDF_OUT,$(VIEW)); rm -f "$$out"
	@$(MAKE) --no-print-directory check
	@$(MAKE) --no-print-directory print-pdf VIEW=$(VIEW)

# Print the already built and checked site; use make pdf.
print-pdf: node_modules
	@$(call PDF_OUT,$(VIEW)); \
	if [ "$(VIEW)" = internal ]; then \
		if [ "$$($(GET) internal.enabled)" != true ]; then echo "internal part disabled in guide.yaml; no internal PDF" >&2; exit 1; fi; \
		site=build/site-internal; view=internal; \
	else \
		site=build/site; view=shareable; \
	fi; \
	html=$$site/print_page.html; \
	if [ ! -f "$$html" ]; then echo "print page $$html missing (run make check)" >&2; exit 1; fi; \
	mkdir -p dist; rm -f "$$out"; \
	node $(TOOLS)/print-pdf.mjs --html "$$html" --guide-root . --view $$view --out "$$out" $(PRINT_ARGS) || exit 1; \
	if [ $$view = shareable ]; then \
		$(UV) run --quiet $(TOOLS)/leakcheck.py "$$out" || { rm -f "$$out"; echo "leak check failed; $$out removed" >&2; exit 1; }; \
	else \
		echo "WARNING: $$out contains internal content. Do not share it outside the internal audience."; \
	fi

dist: check
	@$(MAKE) --no-print-directory print-pdf VIEW=shareable
	@if [ "$$($(GET) internal.enabled)" = true ]; then $(MAKE) --no-print-directory print-pdf VIEW=internal; fi
	@slug=$$($(GET) slug) && date=$$($(GET) baseline.captured) || exit 1; \
	name=$$slug-$$date; \
	rm -rf dist/stage dist/$$name.tar.gz dist/$$name-INTERNAL.tar.gz && mkdir -p dist/stage && \
	cp -R build/site dist/stage/$$name && \
	tar -C dist/stage -czf dist/$$name.tar.gz $$name && \
	echo "Created dist/$$name.tar.gz (shareable)" || exit 1; \
	if [ "$$($(GET) internal.enabled)" = true ]; then \
		cp -R build/site-internal dist/stage/$$name-INTERNAL && \
		tar -C dist/stage -czf dist/$$name-INTERNAL.tar.gz $$name-INTERNAL && \
		echo "WARNING: dist/$$name-INTERNAL.tar.gz contains internal content. Do not share it outside the internal audience." || exit 1; \
	fi; \
	rm -rf dist/stage

drift:
	$(UV) run --quiet $(TOOLS)/drift.py --check

clean:
	rm -rf build dist
