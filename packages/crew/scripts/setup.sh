#!/usr/bin/env bash
# setup.sh — Single entry point for pixl-crew setup.
# Idempotent: installs what's missing, updates what's present.
#
# Usage:
#   make setup                     # full setup (plugins + LSP + security + RTK)
#   make setup SKIP_PLUGINS=1      # skip plugin sync
#   make setup SKIP_LSP=1          # skip LSP plugins
#   make setup SKIP_SECURITY=1     # skip Trail of Bits security plugins
#   make setup SKIP_RTK=1          # skip RTK token optimizer

set -euo pipefail

G='\033[0;32m' Y='\033[1;33m' D='\033[2m' R='\033[0m'

# ─── Core Plugins ──────────────────────────────────────────────────────────

PLUGINS=(
  "pixl-crew@pixl-local"
  "ralph-loop@claude-plugins-official"
  "commit-commands@claude-plugins-official"
  "playground@claude-plugins-official"
  "frontend-design@claude-plugins-official"
)

sync_plugins() {
  echo -e "  ${D}core plugins${R}"
  for p in "${PLUGINS[@]}"; do
    local name="${p%%@*}"
    if claude plugin install "$p" > /dev/null 2>&1; then
      echo -e "  ${G}✓${R} ${name}"
    else
      echo -e "  ${Y}✗${R} ${name}"
    fi
  done
}

# ─── LSP Plugins ───────────────────────────────────────────────────────────

LSP_PLUGINS=(
  "typescript-lsp@claude-plugins-official"
  "pyright-lsp@claude-plugins-official"
  "swift-lsp@claude-plugins-official"
)

sync_lsp() {
  echo -e "  ${D}LSP plugins${R}"
  for p in "${LSP_PLUGINS[@]}"; do
    local name="${p%%@*}"
    if claude plugin install "$p" > /dev/null 2>&1; then
      echo -e "  ${G}✓${R} ${name}"
    else
      echo -e "  ${Y}✗${R} ${name}"
    fi
  done
}

# ─── Security Plugins (Trail of Bits) ─────────────────────────────────────

SECURITY_MARKETPLACE="trailofbits/skills"
SECURITY_PLUGINS=(
  "supply-chain-risk-auditor@trailofbits"
  "variant-analysis@trailofbits"
  "property-based-testing@trailofbits"
  "static-analysis@trailofbits"
  "semgrep-rule-creator@trailofbits"
)

sync_security() {
  echo -e "  ${D}security plugins (Trail of Bits)${R}"

  # add marketplace if not present
  if ! claude plugin marketplace list 2>/dev/null | grep -q trailofbits; then
    claude plugin marketplace add "$SECURITY_MARKETPLACE" > /dev/null 2>&1 || true
  fi

  for p in "${SECURITY_PLUGINS[@]}"; do
    local name="${p%%@*}"
    if claude plugin install "$p" > /dev/null 2>&1; then
      echo -e "  ${G}✓${R} ${name}"
    else
      echo -e "  ${Y}✗${R} ${name}"
    fi
  done
}

# ─── RTK (Rust Token Killer) ─────────────────────────────────────────────

setup_rtk() {
  echo -e "  ${D}RTK token optimizer${R}"

  if command -v rtk &>/dev/null; then
    echo -e "  ${G}✓${R} rtk ($(rtk --version 2>/dev/null | head -1))"
  else
    echo -e "  ${Y}!${R} rtk not installed — install for 60-90% Bash token savings:"
    if [[ "$(uname)" == "Darwin" ]]; then
      echo -e "      ${D}brew install rtk${R}"
    else
      echo -e "      ${D}curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh${R}"
    fi
    return 0
  fi

  # Install hook globally (--hook-only avoids conflicting with crew CLAUDE.md, --auto-patch for non-interactive)
  if [[ ! -f "$HOME/.claude/hooks/rtk-rewrite.sh" ]]; then
    if rtk init -g --hook-only --auto-patch > /dev/null 2>&1; then
      echo -e "  ${G}✓${R} rtk hook installed"
    else
      echo -e "  ${Y}✗${R} rtk hook install failed — run manually: rtk init -g"
    fi
  else
    echo -e "  ${G}✓${R} rtk hook (already installed)"
  fi
}

# ─── Post-install fixups ──────────────────────────────────────────────────

fix_hook_permissions() {
  # Ensure all hook scripts are executable (some plugins ship without +x)
  local hooks_dir="$HOME/.claude/plugins/marketplaces"
  if [[ -d "$hooks_dir" ]]; then
    find "$hooks_dir" -path "*/hooks*" -name "*.sh" ! -perm +111 -exec chmod +x {} \; 2>/dev/null || true
  fi
}

# ─── Main ────────────────────────────────────────────────────────────────

echo ""
echo -e "  ${G}pixl-crew${R} setup"
echo ""

[[ "${SKIP_PLUGINS:-}" != "1" ]] && sync_plugins
[[ "${SKIP_LSP:-}" != "1" ]] && sync_lsp
[[ "${SKIP_SECURITY:-}" != "1" ]] && sync_security
[[ "${SKIP_RTK:-}" != "1" ]] && setup_rtk
fix_hook_permissions

echo ""
echo -e "  ${G}✓${R} done"
echo ""
