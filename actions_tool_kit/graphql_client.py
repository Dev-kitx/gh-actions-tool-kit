from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, cast


class GraphQLError(Exception):
    """Raised when the GitHub GraphQL API returns one or more errors."""

    def __init__(self, errors: List[Dict[str, Any]]) -> None:
        self.errors = errors
        messages = "; ".join(e.get("message", str(e)) for e in errors)
        super().__init__(f"GraphQL errors: {messages}")


def graphql(
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    *,
    token: Optional[str] = None,
    url: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a GraphQL query or mutation against the GitHub API.

    Uses stdlib ``urllib`` only — no extra dependencies required.

    Args:
        query: GraphQL query or mutation string.
        variables: Optional dict of variables referenced in the query.
        token: GitHub token. Falls back to ``GITHUB_TOKEN`` env var.
        url: GraphQL endpoint. Falls back to ``GITHUB_GRAPHQL_URL`` or
             ``https://api.github.com/graphql``.

    Returns:
        The ``data`` dict from the GraphQL response.

    Raises:
        RuntimeError: When no token is available from any source.
        GraphQLError: When the response contains one or more GraphQL errors.
        urllib.error.HTTPError: On non-200 HTTP responses.

    Example::

        from actions_tool_kit import graphql

        data = graphql(
            \"\"\"
            query($owner: String!, $repo: String!) {
              repository(owner: $owner, name: $repo) {
                stargazerCount
                description
              }
            }
            \"\"\",
            variables={"owner": "actions", "repo": "toolkit"},
        )
        print(data["repository"]["stargazerCount"])
    """
    resolved_token = token or os.getenv("GITHUB_TOKEN")
    if not resolved_token:
        raise RuntimeError(
            "No GitHub token found. Pass token= or set the GITHUB_TOKEN "
            "environment variable."
        )

    endpoint: str = url or os.getenv("GITHUB_GRAPHQL_URL") or "https://api.github.com/graphql"

    payload = json.dumps({"query": query, "variables": variables or {}}).encode()

    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {resolved_token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        result: Dict[str, Any] = json.loads(resp.read())

    if "errors" in result:
        raise GraphQLError(result["errors"])

    return cast(Dict[str, Any], result.get("data", {}))


__all__ = ["GraphQLError", "graphql"]
