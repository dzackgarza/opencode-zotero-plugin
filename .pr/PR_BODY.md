# Requested outcome

The README.md is updated to comply with the project standards by including a "why this tool exists" section, an "Install" section that mentions `direnv allow`, a "Checks" section referencing `just` recipes, an "Environment Variables" table, and an MIT "License" section.

# Non-goals

- Modifying the actual plugin implementation.
- Modifying test checks or justfile targets.

# Acceptance checks

- [ ] README.md contains a description of why the tool exists
- [ ] README.md contains an `## Install` section mentioning `direnv allow`
- [ ] README.md contains a `## Checks` section referencing `just`
- [ ] README.md contains an `## Environment Variables` table
- [ ] README.md contains a `## License` section stating MIT

# Evidence to include

- Acceptance check 1:
  - Evidence: exact text added to the top of README.md explaining the tool's purpose
- Acceptance check 2:
  - Evidence: exact output of `grep -A 2 "## Install" README.md`
- Acceptance check 3:
  - Evidence: exact output of `grep -A 2 "## Checks" README.md`
- Acceptance check 4:
  - Evidence: exact table included in README.md for Environment Variables
- Acceptance check 5:
  - Evidence: exact output of `grep -A 2 "## License" README.md`

# Expected changed files

- README.md

# Blockers / open gaps

- None.
