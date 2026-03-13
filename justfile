repo_root := justfile_directory()

justfile-hygiene:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -e "{{repo_root}}/Justfile" ]; then
        echo "Remove Justfile; use lowercase justfile as the single canonical entrypoint." >&2
        exit 1
    fi

# Run all checks
check: justfile-hygiene typecheck test-import

# TypeScript typecheck
typecheck: justfile-hygiene
    direnv exec "{{repo_root}}" bun run typecheck

# Verify Python package imports correctly
test-import: justfile-hygiene
    direnv exec "{{repo_root}}" sh -lc 'cd python && uv run python -c "import zotero_librarian; print(\"Python import OK\")"'

# Run Python tests (requires Zotero running)
test: justfile-hygiene
    direnv exec "{{repo_root}}" sh -lc 'cd python && uv run pytest'

# Test dispatch protocol
dispatch tool args='{}': justfile-hygiene
    direnv exec "{{repo_root}}" sh -lc 'cd python && uv run python -m zotero_librarian._dispatch {{tool}} '"'"'{{args}}'"'"''

# Run MCP server
mcp: justfile-hygiene
    direnv exec "{{repo_root}}" sh -lc 'cd mcp-server && uv run fastmcp run server.py'

# Install TS dependencies
install: justfile-hygiene
    direnv exec "{{repo_root}}" bun install

# Run opencode with this plugin for testing
run prompt: justfile-hygiene
    direnv exec "{{repo_root}}" command opencode run --agent plugin-proof '{{prompt}}'

# Setup npm trusted publisher (one-time manual setup)
setup-npm-trust:
    npm trust github --repository dzackgarza/$(basename {{repo_root}}) --file publish.yml

# Push changes and clear the global OpenCode plugin install cache
push *git_args:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{repo_root}}"
    git push {{git_args}}
    just --justfile "$HOME/justfile" opencode-clear-plugin-install-cache

# Manual publish from local (requires 2FA)
publish: check
    direnv exec "{{repo_root}}" npm publish


# Bump patch version, commit, and tag
bump-patch:
    npm version patch --no-git-tag-version
    git add package.json
    git commit -m "chore: bump version to v$(node -p 'require("./package.json").version')"
    git tag "v$(node -p 'require("./package.json").version')"

# Bump minor version, commit, and tag
bump-minor:
    npm version minor --no-git-tag-version
    git add package.json
    git commit -m "chore: bump version to v$(node -p 'require("./package.json").version')"
    git tag "v$(node -p 'require("./package.json").version')"

# Push commits and tags to trigger CI release
release: check
    git push && git push --tags

