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
    \opencode run --agent Minimal '{{prompt}}'

# Setup npm trusted publisher (one-time manual setup)
setup-npm-trust:
    npm trust github --repository dzackgarza/{{file_stem(justfile_directory())}} --file publish.yml

# Manual publish from local (requires 2FA)
publish:
    npm publish
