# gh-actions-tool-kit

[![CI](https://img.shields.io/github/actions/workflow/status/Dev-kitx/gh-actions-tool-kit/ci.yml?style=for-the-badge&label=CI)](https://github.com/Dev-kitx/gh-actions-tool-kit/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/gh-actions-tool-kit?style=for-the-badge)](https://pypi.org/project/gh-actions-tool-kit/)
[![Python versions](https://img.shields.io/pypi/pyversions/gh-actions-tool-kit?style=for-the-badge)](https://pypi.org/project/gh-actions-tool-kit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](https://github.com/Dev-kitx/gh-actions-tool-kit/blob/main/LICENSE)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue?style=for-the-badge)](https://mypy-lang.org/)
[![codecov](https://img.shields.io/codecov/c/github/Dev-kitx/gh-actions-tool-kit?style=for-the-badge&token=CODECOV_TOKEN)](https://codecov.io/gh/Dev-kitx/gh-actions-tool-kit)

A lightweight, typed Python toolkit for building GitHub Actions. Inspired by [`@actions/core`](https://github.com/actions/toolkit/tree/main/packages/core) and [`actions/github`](https://github.com/actions/toolkit/tree/main/packages/github).

---

## Installation

```bash
pip install gh-actions-tool-kit
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add gh-actions-tool-kit
```

---

## Development

### Running tests

**uv**
```bash
uv run pytest
```

**pipenv**
```bash
pipenv install --dev
pipenv run pytest
```

---

## Modules at a Glance

| Module           | What it provides                                                 |
|------------------|------------------------------------------------------------------|
| `actions_core`   | Inputs, outputs, env vars, logging, annotations, step summary    |
| `context`        | GitHub Actions runtime metadata and typed webhook payload        |
| `actions_exec`   | Run subprocesses with captured or streamed output                |
| `actions_io`     | `which`, `mkdirp`, `rmrf`, `cp`, `mv`, `glob` filesystem helpers |
| `cache`          | Save and restore dependency caches between runs                  |
| `tool_cache`     | Download, extract, and cache tool binaries                       |
| `retry`          | Exponential-backoff retry for flaky network calls                |
| `oidc`           | Fetch OIDC JWTs for cloud provider federation                    |
| `summary`        | Fluent `SummaryBuilder` for rich step summaries                  |
| `artifact`       | Upload and download run artifacts                                |
| `github_client`  | Authenticated PyGitHub client with rate-limit retry              |
| `graphql_client` | GitHub GraphQL client (stdlib only, no extra deps)               |
| `testing`        | `ActionCommandCapture` — parse workflow commands in tests        |
| `checks`         | Create and update GitHub Check Runs with conclusions and annotations |

---

## `actions_core`

### Inputs

```python
from actions_tool_kit import get_input, get_boolean_input, get_multiline_input

# Single-line input (required or optional with default)
token = get_input("token", required=True)
env   = get_input("environment", default="production")

# Boolean input — accepts true/false/yes/no/1/0/on/off
dry_run = get_boolean_input("dry-run")

# Multiline input — returns a list of non-empty lines
files = get_multiline_input("files")
# with:
#   files: |
#     src/main.py
#     src/utils.py
```

| Function                    | Description                                   |
|-----------------------------|-----------------------------------------------|
| `get_input(name)`           | Read a single-line `INPUT_<NAME>` env var     |
| `get_boolean_input(name)`   | Parse a truthy/falsy input into `bool`        |
| `get_multiline_input(name)` | Read newline-delimited input into `list[str]` |

---

### Outputs, Environment, PATH & State

```python
from actions_tool_kit import set_output, export_variable, add_path, save_state, get_state

set_output("digest", "sha256:abc123")          # $GITHUB_OUTPUT
export_variable("DEPLOY_ENV", "staging")        # $GITHUB_ENV
add_path("/opt/my-tool/bin")                    # $GITHUB_PATH
save_state("cache_hit", "true")                 # $GITHUB_STATE (post-step)
hit = get_state("cache_hit")
```

---

### Logging & Annotations

```python
from actions_tool_kit import debug, notice, warning, error

debug("detailed trace — visible only when RUNNER_DEBUG=1")

# Attach annotations to specific file ranges
notice("Unused import", file="src/main.py", line=10, end_line=10, col=1, end_column=20)
warning("Deprecated API", file="src/api.py", line=55, end_line=57, title="Deprecation")
error("Build failed", file="Makefile", line=12, title="Build Error")
```

| Parameter    | Type  | Description                           |
|--------------|-------|---------------------------------------|
| `title`      | `str` | Short label shown in the UI           |
| `file`       | `str` | File path to attach the annotation to |
| `line`       | `int` | Start line number                     |
| `end_line`   | `int` | End line (for range annotations)      |
| `col`        | `int` | Start column number                   |
| `end_column` | `int` | End column (for range annotations)    |

---

### Secrets, Groups & Summary

```python
from actions_tool_kit import set_secret, group, start_group, end_group, append_summary

set_secret(token)   # masks the string in all subsequent log output

with group("Build"):
    # lines here are collapsible in the GitHub UI
    pass

append_summary("## Build passed\n")
```

---

### Debug Mode & Command Control

```python
from actions_tool_kit import is_debug, stop_commands, resume_commands, set_command_echo

if is_debug():                        # RUNNER_DEBUG=1
    debug("extra diagnostics")

# Safely emit untrusted content (not parsed as workflow commands)
token = "stop-safe-token-123"
stop_commands(token)
print(untrusted_user_content)
resume_commands(token)

set_command_echo(True)   # ::echo::on  — echoes every command to the log
set_command_echo(False)  # ::echo::off
```

---

### Failure Helpers

```python
from actions_tool_kit import set_failed, fail_action

set_failed("Lint errors found")          # logs ::error:: but does NOT exit
fail_action("Critical failure — abort")  # logs ::error:: AND raises SystemExit(1)
```

---

## `context`

```python
from actions_tool_kit import context

# Core metadata
print(context.event_name)       # "push"
print(context.sha)              # commit SHA
print(context.ref)              # "refs/heads/main"
print(context.ref_name)         # "main"  (short name — GITHUB_REF_NAME)
print(context.ref_type)         # "branch" or "tag"
print(context.actor)            # who triggered the run
print(context.trigger_actor)    # who triggered the *original* run (differs on re-runs)
print(context.run_id)
print(context.run_number)
print(context.run_attempt)

# Repository
print(context.repo.owner)       # "my-org"
print(context.repo.repo)        # "my-repo"

# Issue / PR identifiers
print(context.issue.number)     # works for both issues and pull_request events
print(context.pr.number)        # None on non-PR events

# Event-type guards
context.is_pr                # bool — payload contains a pull_request
context.is_push              # bool — event_name == "push"
context.is_issue             # bool — event_name == "issues"
context.is_release           # bool — event_name == "release"
context.is_schedule          # bool — event_name == "schedule"
context.is_workflow_dispatch # bool — event_name == "workflow_dispatch"

# PR branches
print(context.head_branch)      # "feature/my-pr"
print(context.base_branch)      # "main"

# Sender
print(context.sender.login)

# Typed payload — attribute access, no more dict["key"]
pr = context.payload.pull_request
if pr:
    print(pr.title, pr.state, pr.head_ref, pr.base_ref, pr.head_sha)
    for label in pr.labels:
        print(label.name, label.color)

issue = context.payload.issue
if issue:
    print(issue.title, issue.state, issue.user.login)

# Push commits
if context.is_push:
    for commit in context.commits:
        print(commit.id, commit.message)
        print(commit.author.name, commit.author.email)
        print("added:", commit.added, "modified:", commit.modified)
```

#### Context Properties

| Property               | Type                            | Description                                |
|------------------------|---------------------------------|--------------------------------------------|
| `event_name`           | `str`                           | Event type (e.g. `push`, `pull_request`)   |
| `ref`                  | `str`                           | Full Git ref (`refs/heads/main`)           |
| `ref_name`             | `str`                           | Short ref name (`main`)                    |
| `ref_type`             | `str`                           | `"branch"` or `"tag"`                      |
| `sha`                  | `str`                           | Commit SHA                                 |
| `workflow`             | `str`                           | Workflow name                              |
| `actor`                | `str`                           | Actor who triggered the run                |
| `trigger_actor`        | `str`                           | Actor who triggered the *original* run     |
| `job`                  | `str`                           | Job name                                   |
| `run_id`               | `int`                           | Unique run ID                              |
| `run_number`           | `int`                           | Run number                                 |
| `run_attempt`          | `int`                           | Retry attempt number                       |
| `api_url`              | `str`                           | GitHub API URL                             |
| `server_url`           | `str`                           | GitHub server URL                          |
| `graphql_url`          | `str`                           | GraphQL endpoint                           |
| `repo`                 | `RepoIdentifier`                | `{owner, repo}`                            |
| `issue`                | `IssueIdentifier`               | `{owner, repo, number}`                    |
| `pr`                   | `PullRequestIdentifier \| None` | `{owner, repo, number}`                    |
| `head_branch`          | `str \| None`                   | PR source branch                           |
| `base_branch`          | `str \| None`                   | PR target branch                           |
| `sender`               | `Sender`                        | Who triggered the event                    |
| `is_pr`                | `bool`                          | Payload contains a pull_request            |
| `is_push`              | `bool`                          | `event_name == "push"`                     |
| `is_issue`             | `bool`                          | `event_name == "issues"`                   |
| `is_release`           | `bool`                          | `event_name == "release"`                  |
| `is_schedule`          | `bool`                          | `event_name == "schedule"`                 |
| `is_workflow_dispatch` | `bool`                          | `event_name == "workflow_dispatch"`        |
| `commits`              | `list[Commit]`                  | Push-event commits (empty on other events) |

---

## `actions_exec`

Run subprocesses with full output control.

```python
from actions_tool_kit import run, ExecResult

# Stream output to the log (default)
result = run("git", ["fetch", "--all"])

# Capture stdout/stderr
result = run("git", ["log", "--oneline", "-5"], capture_output=True)
print(result.stdout)

# Full argv list
result = run(["docker", "build", "-t", "myimage", "."], capture_output=True)

# Raise on non-zero exit
run("pytest", check=True)

# Custom env and working directory
result = run(
    "make", ["test"],
    cwd="/workspace",
    env={"CI": "true"},
    capture_output=True,
)

print(result.returncode)   # int
print(result.success)      # bool (returncode == 0)
print(result.stdout)       # str  (empty when capture_output=False)
print(result.stderr)       # str
```

| Parameter        | Default | Description                                 |
|------------------|---------|---------------------------------------------|
| `cmd`            | —       | Command string or full argv list            |
| `args`           | `()`    | Extra args when `cmd` is a string           |
| `cwd`            | `None`  | Working directory                           |
| `env`            | `None`  | Extra env vars merged on top of current env |
| `capture_output` | `False` | Capture stdout/stderr into result           |
| `check`          | `False` | Raise `RuntimeError` on non-zero exit       |
| `silent`         | `False` | Discard output (sends to `/dev/null`)       |

---

## `actions_io`

```python
from actions_tool_kit import which, mkdirp, rmrf, cp, mv, glob

# Find a tool on PATH
git    = which("git", required=True)   # raises FileNotFoundError if missing
docker = which("docker")               # returns None if absent

# Create a directory tree (no-op if already exists)
mkdirp("/tmp/build/artifacts")

# Delete a file, symlink, or entire directory tree (no-op if absent)
rmrf("/tmp/build")

# Copy a file or directory
cp("src/main.py", "dist/main.py")              # file → file
cp("src/", "dist/src/")                        # dir → dir (recursive)
cp("src/", "dist/")                            # dir into existing dir → dist/src/

# Move a file or directory (parent dirs created automatically)
mv("build/output.zip", "artifacts/output.zip")

# Glob — find files matching a pattern (supports **)
py_files = glob("**/*.py", root="src")         # list[Path], sorted
test_files = glob("tests/test_*.py")           # relative to cwd
```

| Function                  | Description                                                   |
|---------------------------|---------------------------------------------------------------|
| `which(tool)`             | Locate tool on PATH; `required=True` raises if missing        |
| `mkdirp(path)`            | Create directory and all parents (no-op if exists)            |
| `rmrf(path)`              | Delete file, symlink, or directory tree (no-op if absent)     |
| `cp(src, dest)`           | Copy file or directory; dest dir gets source nested inside it |
| `mv(src, dest)`           | Move file or directory; parent dirs created automatically     |
| `glob(pattern, root=cwd)` | Return sorted `list[Path]` matching pattern                   |

---

## `cache`

Save and restore dependency caches between workflow runs using the GitHub Actions cache service.

```python
from actions_tool_kit import restore_cache, save_cache

# Restore a cache at the start of a job
restored_key = restore_cache(
    paths=[".venv"],
    primary_key=f"pip-{hashlib.sha256(open('requirements.txt','rb').read()).hexdigest()}",
    restore_keys=["pip-"],            # fallback prefix match
)

if restored_key:
    print(f"Cache hit: {restored_key}")
else:
    # Cache miss — install dependencies, then save
    subprocess.run(["pip", "install", "-r", "requirements.txt"])
    save_cache(paths=[".venv"], key="pip-abc123")
```

| Function                                          | Description                                                           |
|---------------------------------------------------|-----------------------------------------------------------------------|
| `restore_cache(paths, primary_key, restore_keys)` | Download and extract cached archive; returns matched key or `None`    |
| `save_cache(paths, key)`                          | Archive paths and push to cache service; raises on key conflict (409) |
| `get_cache(keys, paths)`                          | Low-level: query service and return `CacheEntry` or `None`            |

> [!NOTE]
> Requires `ACTIONS_CACHE_URL` and `ACTIONS_RUNTIME_TOKEN` — both are injected automatically
> by GitHub Actions runners. Outside a runner these will raise `RuntimeError`.

---

## `tool_cache`

Download tool binaries, extract archives, and cache them across jobs using the runner tool cache.

```python
from actions_tool_kit import (
    find_cached_tool, download_tool, extract_tar, cache_dir,
)

# Check if the tool is already cached
tool_path = find_cached_tool("ruff", "0.4.*", arch="x64")

if tool_path is None:
    # Download and extract
    archive = download_tool("https://github.com/astral-sh/ruff/releases/download/v0.4.1/ruff-x86_64-unknown-linux-gnu.tar.gz")
    extracted = extract_tar(archive)

    # Cache for future jobs
    tool_path = cache_dir(extracted, "ruff", "0.4.1", arch="x64")

# Add the cached binary to PATH
import os
os.environ["PATH"] = f"{tool_path}:{os.environ['PATH']}"
```

| Function           | Signature                         | Description                                                            |
|--------------------|-----------------------------------|------------------------------------------------------------------------|
| `download_tool`    | `(url, dest=None)`                | Download a file; returns `Path` to local copy                          |
| `extract_tar`      | `(file, dest=None, flags="r:gz")` | Extract tar archive; returns extraction dir                            |
| `extract_zip`      | `(file, dest=None)`               | Extract zip archive; returns extraction dir                            |
| `cache_dir`        | `(src, tool, version, arch=None)` | Copy dir into `RUNNER_TOOL_CACHE/{tool}/{version}/{arch}/`             |
| `find_cached_tool` | `(tool, version_spec, arch=None)` | Find cached tool dir; supports `*` wildcards; returns `Path` or `None` |

> [!NOTE]
> `cache_dir` and `find_cached_tool` require `RUNNER_TOOL_CACHE`. `download_tool`,
> `extract_tar`, and `extract_zip` work anywhere and have no runner dependency.

---

## `retry`

```python
from actions_tool_kit import retry

result = retry(
    lambda: call_flaky_api(),
    max_attempts=5,
    delay=1.0,
    backoff=2.0,
    exceptions=(IOError, TimeoutError),
    on_retry=lambda attempt, exc: warning(f"Attempt {attempt} failed: {exc}"),
)
```

| Parameter      | Default        | Description                                       |
|----------------|----------------|---------------------------------------------------|
| `fn`           | —              | Zero-argument callable to retry                   |
| `max_attempts` | `3`            | Total invocations including the first             |
| `delay`        | `1.0`          | Seconds before the second attempt                 |
| `backoff`      | `2.0`          | Delay multiplier applied after each failure       |
| `exceptions`   | `(Exception,)` | Exception types that trigger a retry              |
| `on_retry`     | `None`         | Callback `(attempt: int, exc: Exception) -> None` |

---

## `oidc`

Fetch OIDC JWTs for keyless authentication with AWS, GCP, Azure, etc.

```python
from actions_tool_kit import get_id_token

# Requires: permissions: id-token: write
jwt = get_id_token()

# With a specific audience (e.g. GCP Workload Identity)
jwt = get_id_token(audience="https://iam.googleapis.com/")
```

> [!NOTE]
> The workflow must declare `permissions: id-token: write`. The function raises
> `RuntimeError` when `ACTIONS_ID_TOKEN_REQUEST_URL` or `ACTIONS_ID_TOKEN_REQUEST_TOKEN`
> are absent.

---

## `summary` — SummaryBuilder

Fluent builder for rich step summaries.

```python
from actions_tool_kit import SummaryBuilder

(
    SummaryBuilder()
    .add_heading("Deploy Report")
    .add_table(
        headers=["Service", "Version", "Status"],
        rows=[
            ["api",    "1.4.0", ":white_check_mark: Healthy"],
            ["worker", "1.4.0", ":x: Degraded"],
        ],
    )
    .add_separator()
    .add_code_block("kubectl rollout status deploy/api", lang="sh")
    .add_link("Full logs", "https://grafana.internal/d/api")
    .write()
)
```

| Method                               | Description                          |
|--------------------------------------|--------------------------------------|
| `add_heading(text, level=1)`         | `#`–`######` heading                 |
| `add_paragraph(text)`                | Plain paragraph                      |
| `add_table(headers, rows)`           | GFM table                            |
| `add_list(items, ordered=False)`     | Bullet or numbered list              |
| `add_code_block(code, lang="")`      | Fenced code block                    |
| `add_separator()`                    | Horizontal rule                      |
| `add_link(label, url)`               | Hyperlink                            |
| `add_image(src, alt, width, height)` | HTML `<img>` tag                     |
| `add_raw(text)`                      | Raw markdown passthrough             |
| `build()`                            | Return accumulated markdown as `str` |
| `write()`                            | Flush to `$GITHUB_STEP_SUMMARY`      |
| `clear()`                            | Reset the builder                    |

---

## `artifact`

Upload and download run artifacts via the GitHub Actions artifact service.

```python
from actions_tool_kit.artifact import ArtifactClient, upload_artifact, download_artifact

# Convenience wrappers
upload_artifact("test-results", ["results/junit.xml", "results/coverage.xml"])
download_artifact("test-results", dest="./downloaded")

# Or use the client directly
client = ArtifactClient()
for a in client.list_artifacts():
    print(a.name, a.size)
client.download_artifact("build-logs", dest="./logs")
```

> [!NOTE]
> Requires `ACTIONS_RUNTIME_URL` and `ACTIONS_RUNTIME_TOKEN`, which the runner
> injects automatically on GitHub-hosted runners.

---

## `github_client`

```python
from actions_tool_kit import get_github_client, call_with_rate_limit_retry

# Create a client — token from GITHUB_TOKEN env var or explicit
gh = get_github_client()
gh = get_github_client(token="ghp_...", timeout=30, per_page=100)

# Basic usage
repo = gh.get_repo("my-org/my-repo")
repo.create_issue(title="Found a bug", body="Steps to reproduce...")

# Wrap any API call with automatic rate limit retry
repo = call_with_rate_limit_retry(
    lambda: gh.get_repo("my-org/my-repo"),
    max_attempts=3,
    on_rate_limit=lambda attempt, wait: warning(f"Rate limited, retrying in {wait:.0f}s"),
)
```

PyGithub types are re-exported from this package so you never need to import PyGithub directly:

```python
from actions_tool_kit import Github, Auth, GithubException, RateLimitExceededException

def process(client: Github) -> None:
    try:
        repo = client.get_repo("my-org/my-repo")
    except GithubException as e:
        error(f"GitHub API error {e.status}: {e.data}")
```

### `call_with_rate_limit_retry`

Retries a callable on GitHub rate limit errors, sleeping until the `x-ratelimit-reset` timestamp before each retry. Falls back to exponential backoff (30 s, 60 s, …) when no reset header is present.

| Parameter       | Default | Description                                                                     |
|-----------------|---------|---------------------------------------------------------------------------------|
| `fn`            | —       | Zero-argument callable wrapping one or more PyGitHub calls                      |
| `max_attempts`  | `3`     | Total attempts including the first                                              |
| `on_rate_limit` | `None`  | Callback `(attempt: int, wait_seconds: float) -> None` called before each sleep |

Catches `RateLimitExceededException` and `GithubException` with status 403 or 429. All other exceptions propagate immediately.

---

## `graphql_client`

Execute GitHub GraphQL queries without adding extra dependencies — uses stdlib `urllib` only.

```python
from actions_tool_kit import graphql, GraphQLError

# Query — GITHUB_TOKEN is used automatically
data = graphql(
    """
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $number) {
          title
          reviewDecision
          reviews(last: 5) {
            nodes { author { login } state }
          }
        }
      }
    }
    """,
    variables={"owner": "my-org", "repo": "my-repo", "number": 42},
)
pr = data["repository"]["pullRequest"]
print(pr["title"], pr["reviewDecision"])

# Mutation
graphql(
    """
    mutation($input: AddCommentInput!) {
      addComment(input: $input) {
        subject { id }
      }
    }
    """,
    variables={"input": {"subjectId": "PR_...", "body": "LGTM!"}},
)

# Handle errors
try:
    data = graphql("{ viewer { login } }")
except GraphQLError as e:
    error("GraphQL failed", title=e.errors[0].get("message"))
```

| Parameter   | Description                                                                           |
|-------------|---------------------------------------------------------------------------------------|
| `query`     | GraphQL query or mutation string                                                      |
| `variables` | Optional dict of variables                                                            |
| `token`     | Override token (default: `GITHUB_TOKEN`)                                              |
| `url`       | Override endpoint (default: `GITHUB_GRAPHQL_URL` or `https://api.github.com/graphql`) |

Returns the `data` dict from the response. Raises `GraphQLError` when the response contains errors.

> [!TIP]
> GitHub's GraphQL API is the only way to access Projects v2, PR review threads,
> discussions, and many other resources not available via REST.

---

## Models

All payload sub-objects are fully typed — no more `dict["key"]` access.

```python
from actions_tool_kit.models import (
    IssuePayload, PullRequestPayload, CommentPayload,
    UserInfo, Label,
    Commit, CommitAuthor,
    RepoIdentifier, IssueIdentifier, PullRequestIdentifier,
    WebhookPayload, PayloadRepository, RepoOwner, Sender,
)
```

| Class                | Key fields                                                                                              |
|----------------------|---------------------------------------------------------------------------------------------------------|
| `IssuePayload`       | `number`, `title`, `body`, `state`, `user`, `labels`                                                    |
| `PullRequestPayload` | `number`, `title`, `state`, `head_ref`, `base_ref`, `head_sha`, `base_sha`, `merged`, `draft`, `labels` |
| `CommentPayload`     | `id`, `body`, `user`                                                                                    |
| `UserInfo`           | `login`, `type`                                                                                         |
| `Label`              | `name`, `color`                                                                                         |
| `Commit`             | `id`, `message`, `author`, `url`, `added`, `removed`, `modified`                                        |
| `CommitAuthor`       | `name`, `email`, `username`                                                                             |

---

## `testing` — ActionCommandCapture

Parse workflow commands emitted during tests without raw string matching.

```python
from actions_tool_kit.testing import ActionCommandCapture
from actions_tool_kit import notice, warning, error

def test_my_action_annotations():
    with ActionCommandCapture() as cap:
        notice("Deployment started", title="Deploy", file="deploy.py", line=10)
        warning("Slow response", file="api.py", line=55, end_line=60)
        error("Build failed")

    assert cap.notices[0].message == "Deployment started"
    assert cap.notices[0].props["title"] == "Deploy"
    assert cap.notices[0].props["file"] == "deploy.py"

    assert cap.warnings[0].props["endLine"] == "60"
    assert cap.errors[0].message == "Build failed"

    # Filter by any command name
    all_notices = cap.of_type("notice")
```

| Attribute            | Description                                    |
|----------------------|------------------------------------------------|
| `cap.commands`       | All `CapturedCommand` objects in order         |
| `cap.notices`        | `::notice::` commands                          |
| `cap.warnings`       | `::warning::` commands                         |
| `cap.errors`         | `::error::` commands                           |
| `cap.debug_messages` | `::debug::` commands                           |
| `cap.of_type(name)`  | Filter by any command name                     |
| `cap.raw_lines`      | Every stdout line including non-command output |

---

## `checks` — CheckRun

Create and manage GitHub Check Runs independently of the job outcome. Requires
`permissions: checks: write` in the workflow.

```python
from actions_tool_kit.checks import CheckRun, Annotation

# Context manager — auto-transitions to in_progress on enter,
# success/failure on exit depending on whether an exception is raised.
with CheckRun.create("mypy", head_sha=context.sha) as check:
    check.update(summary="Running type checks…")
    violations = run_mypy()
    check.complete(
        conclusion="failure" if violations else "success",
        summary=f"{len(violations)} error(s) found",
        annotations=[
            Annotation(
                path=v.file,
                start_line=v.line,
                end_line=v.line,
                annotation_level="failure",
                message=v.message,
                title=v.code,
            )
            for v in violations
        ],
    )
```

### `CheckRun.create`

| Parameter  | Default             | Description                                 |
|------------|---------------------|---------------------------------------------|
| `name`     | —                   | Display name shown in the Checks tab        |
| `head_sha` | —                   | Commit SHA to attach the check to           |
| `token`    | `GITHUB_TOKEN`      | Token with `checks:write` scope             |
| `repo`     | `GITHUB_REPOSITORY` | `"owner/repo"` slug                         |
| `status`   | `"queued"`          | Initial status                              |
| `title`    | `None`              | Short output title shown in the check panel |
| `summary`  | `None`              | Markdown summary shown in the check panel   |
| `api_url`  | `GITHUB_API_URL`    | Override the GitHub API base URL            |

### `.update` / `.complete`

| Method                                                        | Description                                                    |
|---------------------------------------------------------------|----------------------------------------------------------------|
| `.update(status, title, summary, details, annotations)`       | Mid-run progress update; batches >50 annotations automatically |
| `.complete(conclusion, title, summary, details, annotations)` | Mark completed with a final conclusion                         |

### `Annotation`

| Field              | Type             | Description                                               |
|--------------------|------------------|-----------------------------------------------------------|
| `path`             | `str`            | File path relative to the repo root                       |
| `start_line`       | `int`            | Line where the annotation begins                          |
| `end_line`         | `int`            | Line where the annotation ends                            |
| `annotation_level` | `str`            | `"notice"`, `"warning"`, or `"failure"`                   |
| `message`          | `str`            | Body text shown in the GitHub UI                          |
| `title`            | `str \| None`    | Short label displayed above the message                   |
| `start_column`     | `int \| None`    | Starting column (single-line annotations only)            |
| `end_column`       | `int \| None`    | Ending column (single-line annotations only)              |
| `raw_details`      | `str \| None`    | Extra detail shown in a collapsed section                 |

> [!NOTE]
> `start_column` and `end_column` are silently dropped when `start_line != end_line`
> — the GitHub API rejects them on multi-line ranges.

---

## Example Actions

### Composite Action

A composite action runs Python steps directly on the runner — no Docker image required.

**`action.yml`**
```yaml
name: "Python Linter"
description: "Lint Python files changed in a PR and annotate them inline"
author: "your-handle"

inputs:
  python-version:
    description: "Python version to use"
    default: "3.11"
  files:
    description: "Newline-delimited list of files to lint (auto-detects changed files when blank)"
    required: false

outputs:
  violations:
    description: "Total number of lint violations found"
    value: ${{ steps.lint.outputs.violations }}

runs:
  using: "composite"
  steps:
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ inputs.python-version }}

    - name: Install dependencies
      shell: bash
      run: pip install gh-actions-tool-kit ruff

    - name: Run linter
      id: lint
      shell: python
      env:
        INPUT_FILES: ${{ inputs.files }}
      run: |
        import json
        from actions_tool_kit import (
            get_multiline_input, set_output, notice, warning, is_debug,
            debug, group, context, run, fail_action, SummaryBuilder,
        )

        files = get_multiline_input("files")
        if not files and context.is_pr:
            pr = context.payload.pull_request
            r = run(
                "git",
                ["diff", "--name-only", "--diff-filter=d", pr.base_sha, pr.head_sha],
                capture_output=True, check=True,
            )
            files = [f for f in r.stdout.splitlines() if f.endswith(".py")]

        if not files:
            notice("No Python files to lint.")
            set_output("violations", "0")
            raise SystemExit(0)

        violations = 0
        with group(f"Linting {len(files)} file(s)"):
            for path in files:
                r = run(
                    "ruff", ["check", "--output-format=json", path],
                    capture_output=True,
                )
                if is_debug():
                    debug(f"ruff exit={r.returncode} path={path}")
                if not r.success:
                    for diag in json.loads(r.stdout or "[]"):
                        loc = diag.get("location", {})
                        end = diag.get("end_location", {})
                        warning(
                            diag["message"],
                            title=diag.get("code", "ruff"),
                            file=diag["filename"],
                            line=loc.get("row"),
                            end_line=end.get("row"),
                            col=loc.get("column"),
                            end_column=end.get("column"),
                        )
                        violations += 1

        set_output("violations", str(violations))
        SummaryBuilder() \
            .add_heading("Lint Results") \
            .add_table(
                headers=["Files checked", "Violations"],
                rows=[[str(len(files)), str(violations)]],
            ) \
            .write()

        if violations:
            fail_action(f"{violations} violation(s) found.")
```

**Workflow using this action:**
```yaml
name: Lint
on: [pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: your-org/python-linter-action@v1
        with:
          python-version: "3.12"
```

---

### Docker Action

A Docker action runs inside a container — useful for reproducible environments or
actions that need specific system-level dependencies.

**`action.yml`**
```yaml
name: "Docker Deploy Action"
description: "Build, push, and deploy a container image with OIDC cloud auth and PR comments"
author: "your-handle"

inputs:
  image:
    description: "Docker image name (e.g. my-org/my-app)"
    required: true
  tag:
    description: "Image tag"
    default: "latest"
  registry:
    description: "Container registry hostname"
    default: "ghcr.io"
  token:
    description: "Registry / GitHub token"
    required: true

outputs:
  image-digest:
    description: "SHA256 digest of the pushed image"

runs:
  using: "docker"
  image: "Dockerfile"
```

**`Dockerfile`**
```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      docker-cli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /action
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY entrypoint.py .
ENTRYPOINT ["python", "/action/entrypoint.py"]
```

**`requirements.txt`**
```
gh-actions-tool-kit
PyGithub
```

**`entrypoint.py`**
```python
from actions_tool_kit import (
    get_input, set_output, set_secret, group,
    notice, warning, fail_action,
    run, which, mkdirp, rmrf,
    retry, get_id_token,
    context, get_github_client,
    SummaryBuilder,
)


def main() -> None:
    image    = get_input("image",    required=True)
    tag      = get_input("tag",      default="latest")
    registry = get_input("registry", default="ghcr.io")
    token    = get_input("token",    required=True)
    set_secret(token)

    full_image = f"{registry}/{image}:{tag}"
    build_dir  = "/workspace/build"
    mkdirp(build_dir)
    which("docker", required=True)

    with group("Docker build"):
        run(["docker", "build", "-t", full_image, "."], check=True)

    with group("Docker push"):
        retry(
            lambda: run(["docker", "push", full_image], check=True),
            max_attempts=3,
            delay=5.0,
            on_retry=lambda n, e: warning(f"Push attempt {n} failed: {e}"),
        )

    digest_result = run(
        ["docker", "inspect", "--format={{index .RepoDigests 0}}", full_image],
        capture_output=True, check=True,
    )
    digest = digest_result.stdout.strip().split("@")[-1]
    set_output("image-digest", digest)

    # OIDC — keyless cloud authentication (optional)
    try:
        get_id_token(audience="https://iam.googleapis.com/")
        notice("OIDC token obtained for GCP federation")
    except RuntimeError:
        notice("OIDC not requested — skipping cloud federation")

    # Comment on the PR with the pushed image details
    if context.is_pr:
        gh   = get_github_client(token=token)
        repo = gh.get_repo(f"{context.repo.owner}/{context.repo.repo}")
        pr   = repo.get_pull(context.pr.number)
        pr.create_issue_comment(
            f"**Docker image pushed** `{full_image}`\nDigest: `{digest}`"
        )

    SummaryBuilder() \
        .add_heading("Deploy Summary") \
        .add_table(
            headers=["Field", "Value"],
            rows=[
                ["Image",        f"`{full_image}`"],
                ["Digest",       f"`{digest}`"],
                ["Registry",     registry],
                ["Triggered by", context.trigger_actor or context.actor],
                ["Commit",       context.sha[:7]],
            ],
        ) \
        .write()

    rmrf(build_dir)
    notice(f"Pushed {full_image} ({digest})")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        fail_action(str(exc))
```

**Workflow using this action:**
```yaml
name: Deploy
on:
  push:
    branches: [main]

permissions:
  contents: read
  packages: write
  id-token: write   # required for get_id_token()

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: your-org/docker-deploy-action@v1
        with:
          image: my-org/my-app
          tag: ${{ github.sha }}
          registry: ghcr.io
          token: ${{ secrets.GITHUB_TOKEN }}
```

---

## Credits

Inspired by [`@actions/core`](https://github.com/actions/toolkit/tree/main/packages/core) and [`actions/github`](https://github.com/actions/toolkit/tree/main/packages/github).

## License

MIT License © 2024 AB
