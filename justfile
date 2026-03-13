# opencode-zotero-plugin justfile

# Run all checks
check: typecheck test-import

# TypeScript typecheck
typecheck:
    bun run typecheck

# Verify Python package imports correctly
test-import:
    cd python && uv run python -c "import zotero_librarian; print('Python import OK')"

# Run Python tests (requires Zotero running)
test:
    cd python && uv run pytest

# Test dispatch protocol
dispatch tool args='{}':
    cd python && uv run python -m zotero_librarian._dispatch {{tool}} '{{args}}'

# Run MCP server
mcp:
    cd mcp-server && uv run fastmcp run server.py

# Install TS dependencies
install:
    bun install

# Run opencode with this plugin for testing
run prompt:
    \opencode run --agent plugin-proof '{{prompt}}'

# Setup npm trusted publisher (one-time manual setup)
setup-npm-trust:
    npm trust github --repository dzackgarza/$(basename {{justfile_directory()}}) --file publish.yml

# Push changes and clear the global OpenCode plugin install cache
push *git_args:
    #!/usr/bin/env bash
    set -euo pipefail
    git push {{git_args}}
    just --justfile "$HOME/justfile" opencode-clear-plugin-install-cache

# Manual publish from local (requires 2FA)
publish:
    npm publish
