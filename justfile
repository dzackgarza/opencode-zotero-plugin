set fallback := true

# opencode-zotero-plugin justfile

# Run all checks
check: typecheck

# TypeScript typecheck
typecheck:
    bun run typecheck

# Install TS dependencies
install:
    bun install

# Run opencode with this plugin for testing
run prompt:
    \opencode run --agent Minimal '{{ prompt }}'

# Setup npm trusted publisher (one-time manual setup)
setup-npm-trust:
    npm trust github --repository dzackgarza/{{ file_stem(justfile_directory()) }} --file publish.yml

# Manual publish from local (requires 2FA)
publish:
    npm publish

set unstable := true
