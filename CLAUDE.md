# gh-actions-tool-kit

Python toolkit for building GitHub Actions, mirroring `@actions/core` and `actions/github`.

## Common commands

```bash
uv sync --extra dev       # install deps (first time or after pyproject.toml changes)
uv run pytest             # run all 259 tests
uv run mypy actions_tool_kit/   # type-check (must pass clean)
make run-pytest           # same as uv run pytest with coverage + junit xml
make run-mypy             # same as uv run mypy
```

## Architecture constraints

- **stdlib-only HTTP** — all modules use `urllib` directly; no `requests` or `httpx`. The only allowed extra dep is `PyGithub`, used exclusively in `github_client.py`.
- **No new runtime dependencies** — if a feature can be done with stdlib, do it that way.
- **py.typed marker** — `actions_tool_kit/py.typed` is an empty PEP 561 marker; keep it. Declared in `pyproject.toml` under `[tool.setuptools] package-data`.

## Non-obvious patterns

- **`os.getenv` with guaranteed `str`** — use triple-or: `arg or os.getenv("VAR") or "default"`. Never use `os.getenv("VAR", "default")` when the result flows into something typed `str` and `arg` can be `None`.
- **`__exit__` return type** — always annotate as `Literal[False]`, not `bool` or `None`, or mypy will complain.
- **`@contextmanager` return type** — must be `Iterator[None]`, not `ContextManager[None]`.
- **`context.py __init__`** — must have `-> None` annotation; missing it causes mypy to skip the body, making all instance attributes type as `Any` and cascading errors into every property.
- **Annotation batching** — GitHub Checks API accepts max 50 annotations per request. `checks.py` batches automatically in both `update()` and `complete()`.
- **OIDC audience encoding** — use `urllib.parse.quote(audience, safe='')` (not default `safe='/'`) so `/` in URLs gets percent-encoded.

## Module list

| File                | Mirrors                   |
|---------------------|---------------------------|
| `actions_core.py`   | `@actions/core`           |
| `actions_exec.py`   | `@actions/exec`           |
| `actions_io.py`     | `@actions/io`             |
| `artifact.py`       | `@actions/artifact`       |
| `cache.py`          | `@actions/cache`          |
| `checks.py`         | GitHub Checks API         |
| `context.py`        | `@actions/github` context |
| `github_client.py`  | `@actions/github` octokit |
| `graphql_client.py` | GraphQL client            |
| `models.py`         | shared dataclasses        |
| `oidc.py`           | `@actions/core` OIDC      |
| `payload_parser.py` | webhook payload parsing   |
| `retry.py`          | `@actions/github` retry   |
| `summary.py`        | `@actions/core` summary   |
| `testing.py`        | test helpers              |
| `tool_cache.py`     | `@actions/tool-cache`     |

## Known gaps (not yet implemented)

- No dedicated CI workflow for PRs (tests only run in the PyPI publish workflow)
- No CHANGELOG
- `__main__.py` CLI has 0% test coverage
