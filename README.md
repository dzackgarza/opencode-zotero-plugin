[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/I2I57UKJ8)

# zotero

Maintain Zotero libraries with this Python toolkit. It includes task and skill materials for efficient library maintenance. This directory contains library code and operator entrypoints rather than an OpenCode plugin package.

## Install

Run these commands to install:

```bash
cd /home/dzack/opencode-plugins/zotero
just install
```

## Surface

Access key components here:

- **Library code**: [`zotero/_dev/src/zotero_librarian`](/home/dzack/opencode-plugins/zotero/_dev/src/zotero_librarian/__init__.py)
- **Operator entrypoint**: [`zotero/agents.py`](/home/dzack/opencode-plugins/zotero/agents.py)
- **Skill docs**: [`zotero/SKILL.md`](/home/dzack/opencode-plugins/zotero/SKILL.md)

Dependencies:

- **Runtime**: Python 3.13+, `pyzotero`, `httpx`
- **arXiv extras (optional)**: `arxiv`, `python-dateutil`, `pymupdf4llm`
- **Tests**: A live Zotero 7 local API is required for many tests.

## Checks

Execute tests with just:

```bash
just test
```
