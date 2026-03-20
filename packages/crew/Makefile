.PHONY: setup release check help install-local scaffold export-skills export-skills-dry

setup:
	@bash scripts/setup.sh

release:
	@bash scripts/release.sh

check:
	@claude plugin list

help:
	@echo "make setup                 Install/update plugins"
	@echo "make setup SKIP_PLUGINS=1  Skip plugin sync"
	@echo "make release               Bump patch, tag, push, refresh"
	@echo "make release BUMP=minor    Bump minor version"
	@echo "make release BUMP=major    Bump major version"
	@echo "make check                 Print installed plugins"
	@echo "make scaffold STACK=nextjs  Interactive project scaffold"
	@echo "make install-local         Register local pixl-crew path"

STACK ?= nextjs
scaffold:
	@bash scripts/scaffold-interactive.sh studio/stacks/$(STACK)/

install-local:
	@bash scripts/install-local.sh

export-skills:
	@python3 scripts/export-skills-zip.py --mega-zip

export-skills-dry:
	@python3 scripts/export-skills-zip.py --dry-run --verbose
